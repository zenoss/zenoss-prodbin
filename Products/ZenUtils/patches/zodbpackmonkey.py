##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2014, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################

"""
This module patches relstorage.adapters.packundo.HistoryFreePackUndo to prevent
the creation of POSKey errors during the execution of zodbpack.
Patched methods:
    def _pre_pack_main(self, conn, cursor, pack_tid, get_references)
    def _add_refs_for_oids(self, cursor, oids, get_references):
    def pack(self, pack_tid, sleep=None, packed_func=None)
    def _pack_cleanup(self, conn, cursor)
"""

import logging
from Products.ZenUtils.Utils import monkeypatch

import os
import pickle

import time

log = logging.getLogger("zenoss.zodbpack.monkey")

class ObjectRelations(object):
    def __init__(self, oid, tid):
        self.oid = oid
        self.tid = tid
        self.refs_to = []
        self.refs_from = []

class ZodbPackMonkeyHelper(object):

    TABLE_NAME = 'object_reverse_ref'
    PICKLE_FILENAME = 'zodbpack_skipped_oids.pickle'
    ROLLBACK_OIDS_FILENAME = 'zodbpack_rollback_oids.txt'

    def create_table(self, cursor):
        """ as of transaction tid, zoid_from x had a reference to zoid y """
        sql = """CREATE TABLE IF NOT EXISTS {0}(
                    zoid        BIGINT NOT NULL,
                    zoid_from   BIGINT NOT NULL,
                    tid         BIGINT,
                    PRIMARY KEY(zoid, zoid_from)
                ) ENGINE = MyISAM;""".format(self.TABLE_NAME)
        cursor.execute(sql)

    def get_current_database(self, cursor):
        sql = """SELECT DATABASE();"""
        cursor.execute(sql)
        return cursor.fetchall()[0][0]

    def table_exists(self, cursor):
        """ Checks if the reverse reference table exists """
    	exists = False
    	current_db = self.get_current_database(cursor)
    	sql = """SELECT table_name FROM information_schema.tables WHERE table_schema = '{0}' AND table_name = '{1}';""".format(current_db, self.TABLE_NAME)
    	cursor.execute(sql)
    	if cursor.rowcount == 1:
    		exists = True
    	return exists

    def delete_batch(self, cursor, batch):
        values = ", ".join([ "({0},{1})".format(oid, tid) for oid, tid in batch ])
        sql = """DELETE FROM object_state WHERE (zoid, tid) IN ({0})""".format(values)
        cursor.execute(sql)
        return cursor.rowcount

    def force_ref_tables_initialization(self, cursor):
		""" 
		Removes all data from tables 'object_refs_added' and 'object_ref'
		that will cause the initialization of the references table during the 
        pre-pack process
		"""
		sql = "TRUNCATE object_refs_added;"
		cursor.execute(sql)
		sql = "TRUNCATE object_ref;"
		cursor.execute(sql)

    def update_reverse_references(self, cursor, oids, add_refs):
        """
        updates the reverse references for objects referenced by objects in 'oids'
        """
        # removes the previous reverse references for the passed oids
        values = ','.join(str(oid) for oid in oids)
        sql = """DELETE FROM {0} WHERE zoid_from IN ({1});""".format(self.TABLE_NAME, values)
        cursor.execute(sql)

        # adds new reverse references from the passed oids
        if len(add_refs) > 0:
            values = ','.join([ "({0}, {1}, {2})".format(str(to_zoid), str(zoid_from), str(tid)) for (zoid_from, tid, to_zoid) in add_refs ])
            sql = """INSERT INTO {0} (zoid, zoid_from, tid) VALUES {1}""".format(self.TABLE_NAME, values)
            cursor.execute(sql)

    def log_exception(self, e, info=''):
        log.error("Monkey patch for zodbpack raised and exception: {0}: {1}".format(info, e))

    def get_refs_to(self, cursor, zoid_from):
    	""" returns the oids 'zoid_from' references to """
        sql = """SELECT zoid, to_zoid FROM {0} WHERE zoid = {1};""".format("object_ref", zoid_from)
        cursor.execute(sql)
        result = cursor.fetchall()
        return set([ oid_to for oid_from, oid_to in result if oid_to!=oid_from ])

    def get_refs_from(self, cursor, zoid):
    	""" returns the oids that reference zoid """
        sql = """SELECT zoid, zoid_from FROM {0} WHERE zoid = {1};""".format(self.TABLE_NAME, zoid)
        cursor.execute(sql)
        result = cursor.fetchall()
        return set([ oid_from for oid, oid_from in result if oid!=oid_from ])

    def _build_relations_dict(self, cursor, oids):
        """
        Builds an 'ObjectRelations' object for each oid in 'oids'
        oids : tuple(oid, tid)
        return dict: keys   => oids
        			 values => ObjectRelations for the oid
        """
        relations_map = {}
        for zoid, tid in oids:
            relations = ObjectRelations(zoid, tid)
            relations.refs_to = self.get_refs_to(cursor, zoid)
            relations.refs_from  = self.get_refs_from(cursor, zoid)
            relations_map[zoid] = relations
        return relations_map

    def _get_connected_oids_to(self, oid, relations, visited):
        """ returns objects that are at distance 1 from oid and have not been already visited """
        objects = relations[oid].refs_to.union(relations[oid].refs_from)
        assert(len(objects) == len(set(objects)))
        return [ oid for oid in objects if oid in relations and not visited[oid] ]

    def _get_connected_oids(self, initial_oid, relations, visited):
        """ breadth-first search to find all reachable oids from 'oid' """
        connected_oids = []
        queue = set([ initial_oid ])
        while queue:
            current_oid = queue.pop()
            visited[current_oid] = True
            connected_oids.append((current_oid, relations[current_oid].tid))
            queue.update(self._get_connected_oids_to(current_oid, relations, visited))
        return connected_oids

    def group_oids(self, cursor, to_remove):
    	"""
    	Return a list of grouped oids. Each group represents oids that are part
    	of the same 'zenoss object'. All oids in a group have to be deleted in a
    	transactional way to avoid PKE (todos o ninguno)
    	"""
    	relations_dict = MONKEY_HELPER._build_relations_dict(cursor, to_remove)

    	oids_to_remove = [ oid for (oid, tid) in to_remove ]

        assert(len(oids_to_remove) == len(set(oids_to_remove)) == len(to_remove))

    	visited = { oid:False for oid in oids_to_remove }

        grouped_oids = []
        while oids_to_remove:
            oid = oids_to_remove[0]
            connected_oids = MONKEY_HELPER._get_connected_oids(oid, relations_dict, visited)
            grouped_oids.append(connected_oids)
            oids_to_remove = [ oid for oid in visited if not visited[oid] ]

        return grouped_oids

    def _get_count_in_table(self, cursor, oids, table_name, select_fields, where_fields):
        """ method to perform queries needed for tests """
        if not oids:
            return 0
        if isinstance(select_fields, list):
            select_fields = ", ".join(select_fields)
        if isinstance(where_fields, list):
            where_fields =  ", ".join(where_fields)
        values = ", ".join(oids)
        sql = """ SELECT {0} FROM {1} WHERE {2} IN ({3});""".format(select_fields, table_name, where_fields, values)
        cursor.execute(sql)
        return cursor.rowcount

    def _print_test_result(self, text, passed):
        text = text.ljust(50, '.')
        result = "PASSED"
        if not passed:
            result = "FAILED"
        log.info("{0}{1}".format(text, result.rjust(8)))

    def run_post_pack_tests(self, cursor, to_remove, oids_not_removed):
        """ 
        Checks that the db tables have been left in a consistent state
        """
        if len(to_remove) == 0:
            log.info("Validating results: No oids were deleted")
            return

        to_remove = set([ str(oid) for oid, tid in to_remove ])
        not_removed = set([ str(oid) for oid, tid in oids_not_removed])
        removed = to_remove - to_remove.intersection(not_removed)
        log.info("Validating results: {0} oids marked for removal / {1} oids removed / {2} oids skipped to avoid pke.".format(len(to_remove), len(removed), len(not_removed)))

        # Check tables state, deleted oids must no be in any of the tables and 
        # not deleted oids must be in all tables
        # 
        tables = [ "object_state", "object_refs_added" ]
        for table in tables:
            removed_count = self._get_count_in_table(cursor, removed, table, "zoid", "zoid")
            not_removed_count = self._get_count_in_table(cursor, not_removed, table, "zoid", "zoid")
            passed = ( removed_count==0 and not_removed_count==len(not_removed) )
            self._print_test_result("Validating {0}".format(table), passed)

        # removed objects must not have any references from or to in the references tables
        # for references tables check that removed oids are not in the tables
        table = 'object_ref'

        r_from = self._get_count_in_table(cursor, removed, table, "zoid", "zoid")
        r_to = self._get_count_in_table(cursor, removed, table, "zoid", "to_zoid")
        passed = ( r_from==0 and r_to==0 )
        self._print_test_result("Validating {0}".format(table), passed)

        table = self.TABLE_NAME
        r_from = self._get_count_in_table(cursor, removed, table, "zoid", "zoid_from")
        r_to = self._get_count_in_table(cursor, removed, table, "zoid", "zoid")
        passed = ( r_from==0 and r_to==0 )
        self._print_test_result("Validating {0}".format(table), passed)

    def create_pickle(self, skipped_oids, path, filename):
        """
        Creates a pickle of the (oids,tid) that have not been
        packed bc the object changed between pre pack and pack
        phases. This can be useful to find out what orphan oids
        changed during zodbpack.
        """
        try:
            pfile = open(filename, "wb")
            pickle.dump(skipped_oids, pfile)
            pfile.close()
            log.info("Not deleted oids pickled to file: {0}".format(filename))
        except Exception as e:
            self.log_exception(e, "Failed to create pickle with skipped oids")

    def _get_rolledback_oids(self, cursor, skipped_oids):
        if skipped_oids:
            values = ','.join([ str(oid) for oid, tid in skipped_oids])
            sql = """SELECT zoid, tid FROM object_state WHERE zoid IN ({0})""".format(values)
            cursor.execute(sql)
            data = set(cursor.fetchall()) - set(skipped_oids)
            return [ str(oid) for oid, tid in data ]
            
    def export_rolledback_oids_to_file(self, cursor, skipped_oids, filename):
        """ Export to a file the oids that changed between prepack and pack phases """
        try:
            pfile = open(filename, "w")
            rolledback_oids = self._get_rolledback_oids(cursor, skipped_oids)
            pfile.write('-'*75)
            pfile.write('\nThe oids below were marked for deletion by zenossdbpack but a later');
            pfile.write('\ntransaction updated the object before it was deleted.');
            pfile.write('\nTo find out the type of the objects, paste the following code in zendmd:\n');
            pfile.write('-'*75)
            pfile.write('\nfrom ZODB.utils import p64');
            values = ",".join([ oid for oid in rolledback_oids ])
            pfile.write('\nfor oid in [{0}]: print dmd._p_jar[p64(oid)]\n'.format(values));
            pfile.write('-'*75)
            pfile.write('\n')
            pfile.write('\n'.join(rolledback_oids));
            log.info("Mofified oids between pre_pack and pack dumped to file: {0}".format(filename))
        except Exception as e:
            self.log_exception(e, "Failed to create file with skipped oids")

    def export_rolledback_oids(self, cursor, skipped_oids):
        """ """
        try:
            db = self.get_current_database(cursor)
            zenhome = os.environ.get('ZENHOME', os.path.join('opt', 'zenoss'))
            path = os.path.join(zenhome, 'log')

            filename = os.path.join(path, '{0}_{1}'.format(db, self.PICKLE_FILENAME))
            self.create_pickle(skipped_oids, path, filename)

            filename = os.path.join(path, '{0}_{1}'.format(db, self.ROLLBACK_OIDS_FILENAME))
            self.export_rolledback_oids_to_file(cursor, skipped_oids, filename)

        except Exception as e:
            self.log_exception(e, "Failed to export skipped oids")

MONKEY_HELPER = ZodbPackMonkeyHelper()

try:
    from relstorage.adapters.packundo import HistoryFreePackUndo
    @monkeypatch('relstorage.adapters.packundo.HistoryFreePackUndo')
    def _pre_pack_main(self, conn, cursor, pack_tid, get_references):
    	"""Determine what to garbage collect."""

        if not MONKEY_HELPER.table_exists(cursor):
        	log.info("All reference tables will be created from scratch (this may take a while).")
        	MONKEY_HELPER.create_table(cursor)
        	MONKEY_HELPER.force_ref_tables_initialization(cursor)

        stmt = self._script_create_temp_pack_visit
        if stmt:
            self.runner.run_script(cursor, stmt)

        self.fill_object_refs(conn, cursor, get_references)

        log.info("pre_pack: filling the pack_object table")
        # Fill the pack_object table with all known OIDs.
        stmt = """
        %(TRUNCATE)s pack_object;

        INSERT INTO pack_object (zoid, keep, keep_tid)
        SELECT zoid, %(FALSE)s, tid
        FROM object_state;

        -- Keep the root object.
        UPDATE pack_object SET keep = %(TRUE)s
        WHERE zoid = 0;

        -- Keep objects that have been revised since pack_tid.
        UPDATE pack_object SET keep = %(TRUE)s
        WHERE keep_tid > %(pack_tid)s;
        """
        self.runner.run_script(cursor, stmt, {'pack_tid': pack_tid})

        # Traverse the graph, setting the 'keep' flags in pack_object
        self._traverse_graph(cursor)

    from relstorage.adapters.packundo import HistoryFreePackUndo
    @monkeypatch('relstorage.adapters.packundo.HistoryFreePackUndo')
    def _add_refs_for_oids(self, cursor, oids, get_references):
        """Fill object_refs with the states for some objects.

        Returns the number of references added.
        """
        oid_list = ','.join(str(oid) for oid in oids)
        use_base64 = (self.database_name == 'postgresql')

        if use_base64:
            stmt = """
            SELECT zoid, tid, encode(state, 'base64')
            FROM object_state
            WHERE zoid IN (%s)
            """ % oid_list
        else:
            stmt = """
            SELECT zoid, tid, state
            FROM object_state
            WHERE zoid IN (%s)
            """ % oid_list
        self.runner.run_script_stmt(cursor, stmt)

        add_objects = []
        add_refs = []
        for from_oid, tid, state in cursor:
            if hasattr(state, 'read'):
                # Oracle
                state = state.read()
            add_objects.append((from_oid, tid))
            if state:
                state = str(state)
                if use_base64:
                    state = decodestring(state)
                try:
                    to_oids = get_references(state)
                except:
                    log.error("pre_pack: can't unpickle "
                        "object %d in transaction %d; state length = %d" % (
                        from_oid, tid, len(state)))
                    raise
                for to_oid in to_oids:
                    add_refs.append((from_oid, tid, to_oid))

        if not add_objects:
            return 0

        stmt = "DELETE FROM object_refs_added WHERE zoid IN (%s)" % oid_list
        self.runner.run_script_stmt(cursor, stmt)
        stmt = "DELETE FROM object_ref WHERE zoid IN (%s)" % oid_list
        self.runner.run_script_stmt(cursor, stmt)

        stmt = """
        INSERT INTO object_ref (zoid, tid, to_zoid) VALUES (%s, %s, %s)
        """
        self.runner.run_many(cursor, stmt, add_refs)

        stmt = """
        INSERT INTO object_refs_added (zoid, tid) VALUES (%s, %s)
        """
        self.runner.run_many(cursor, stmt, add_objects)

        try:
            MONKEY_HELPER.update_reverse_references(cursor, oids, add_refs)
        except Exception as e:
            MONKEY_HELPER.log_exception(e, "Exception adding oids to reverse reference table")
            raise e

        return len(add_refs)

    #------------------ Functions related to pack method ---------------------

    def get_grouped_oids(cursor, oids_to_remove):
        """ Groups oids to be removed in groups of connected objects """
        group_start = time.time()
        grouped_oids = []
        try:
            grouped_oids = MONKEY_HELPER.group_oids(cursor, oids_to_remove)
        except Exception as e:
            MONKEY_HELPER.log_exception(e, "Exception while grouping oids")
            raise e

        explore_relations_time = time.time() - group_start
        if explore_relations_time > 1:
            explore_relations_time = str(explore_relations_time).split('.')[0]
            log.info("Exploring oid relations took {0} seconds.".format(explore_relations_time))

        return grouped_oids

    from relstorage.adapters.packundo import HistoryFreePackUndo
    @monkeypatch('relstorage.adapters.packundo.HistoryFreePackUndo')
    def remove_isolated_oids(self, conn, cursor, grouped_oids, sleep, packed_func, total, oids_processed):
        """
        objects that not connected to other objects can be safely removed.
        """
        # We'll report on progress in at most .1% step increments
        reportstep = max(total / 1000, 1)
        lastreport = (total - oids_processed) / reportstep * reportstep

        isolated_oids = []
        for oids_group in grouped_oids:
            if len(oids_group) == 1:
                isolated_oids.extend(oids_group)

        packed_list = []
        batch_size = 100
        self._pause_pack_until_lock(cursor, sleep)
        start = time.time()
        while isolated_oids:
            batch = isolated_oids[:batch_size]
            del isolated_oids[:batch_size]

            MONKEY_HELPER.delete_batch(cursor, batch)

            oids_processed = oids_processed + len(batch)

            if time.time() >= start + self.options.pack_batch_timeout:
                conn.commit()
                if packed_func is not None:
                    for oid, tid in packed_list:
                        packed_func(oid, tid)
                    del packed_list[:]
                counter = total - oids_processed
                if counter >= lastreport + reportstep:
                    log.info("pack: processed %d (%.1f%%) state(s)",
                        counter, counter/float(total)*100)
                    lastreport = counter / reportstep * reportstep
                self.locker.release_commit_lock(cursor)
                self._pause_pack_until_lock(cursor, sleep)
                start = time.time()

        if packed_func is not None:
            for oid, tid in packed_list:
                packed_func(oid, tid)
        conn.commit()
        self.locker.release_commit_lock(cursor)

        return oids_processed


    from relstorage.adapters.packundo import HistoryFreePackUndo
    @monkeypatch('relstorage.adapters.packundo.HistoryFreePackUndo')
    def remove_connected_oids(self, conn, cursor, grouped_oids, sleep, packed_func, total, oids_processed):
        """
        connected oids must be removed all or none
        """
        # We'll report on progress in at most .1% step increments
        reportstep = max(total / 1000, 1)
        lastreport = (total - oids_processed) / reportstep * reportstep

        batch_size = 1000 # some batches can be huge and we are holding the commit lock
        prevent_pke_oids = [] # oids that have not been deleted to prevent pkes
        rollbacks = 0
        self._pause_pack_until_lock(cursor, sleep)
        start = time.time()
        for oids_group in grouped_oids:
            if len (oids_group) == 1:
                # isolated oids were processed before 
                continue
            rollback = False
            oid_batches = oids_group[:]
            while oid_batches and not rollback:
                batch = oid_batches[:batch_size]
                del oid_batches[:batch_size]
                count = MONKEY_HELPER.delete_batch(cursor, batch)
                # Check that no objects have been modified between deleting batches
                if count != len(batch):
                    rollback = True
                    break
            if rollback:
                conn.rollback()
                rollbacks = rollbacks + 1
                prevent_pke_oids.extend(oids_group)
            else:
                conn.commit()
                if packed_func is not None:
                    for oid, tid in oids_group:
                        packed_func(oid, tid)

            oids_processed = oids_processed + len(oids_group)
            if time.time() >= start + self.options.pack_batch_timeout:
                counter = total - oids_processed
                if counter >= lastreport + reportstep:
                    log.info("pack: processed %d (%.1f%%) state(s)",
                        counter, counter/float(total)*100)
                    lastreport = counter / reportstep * reportstep
                self.locker.release_commit_lock(cursor)
                self._pause_pack_until_lock(cursor, sleep)
                start = time.time()

        self.locker.release_commit_lock(cursor)

        if prevent_pke_oids:
            log.info("{0} oid groups were not deleted to prevent POSKey Errors. ({1} oids)".format(rollbacks, len(prevent_pke_oids)))
            # unmark the oids from pack_object so _pack_cleanup wont remove them from object_refs_added and object_ref
            for oid, tid in prevent_pke_oids:
                sql = """UPDATE pack_object SET keep = TRUE WHERE zoid={0};""".format(oid)
                cursor.execute(sql)
            conn.commit()
            MONKEY_HELPER.export_rolledback_oids(cursor, prevent_pke_oids)

        return prevent_pke_oids
            
    from relstorage.adapters.packundo import HistoryFreePackUndo
    @monkeypatch('relstorage.adapters.packundo.HistoryFreePackUndo')
    def pack(self, pack_tid, sleep=None, packed_func=None):
        """ Run garbage collection. Requires the information provided by pre_pack. """
        # Read committed mode is sufficient.
        conn, cursor = self.connmanager.open()
        try:
            try:
                stmt = """
                SELECT zoid, keep_tid
                FROM pack_object
                WHERE keep = %(FALSE)s
                """
                self.runner.run_script_stmt(cursor, stmt)
                to_remove = list(cursor)

                total = len(to_remove)
                log.info("pack: will remove %d object(s)", total)

                if total > 0:
                    log.info("Exploring oid relations... (may take a while)")
                    grouped_oids = get_grouped_oids(cursor, to_remove)

                    # Hold the commit lock while packing to prevent deadlocks.
                    # Pack in small batches of transactions only after we are able
                    # to obtain a commit lock in order to minimize the
                    # interruption of concurrent write operations.
                    log.info("Removing objects...")
                    oids_processed = self.remove_isolated_oids(conn, cursor, grouped_oids, sleep, packed_func, total, 0)

                    prevent_pke_oids = self.remove_connected_oids(conn, cursor, grouped_oids, sleep, packed_func, total, oids_processed)

                    self._pack_cleanup(conn, cursor)

                    try:
                        MONKEY_HELPER.run_post_pack_tests(cursor, to_remove, prevent_pke_oids)
                    except Exception as e:
                        MONKEY_HELPER.log_exception(e, "Execption while running tests.")

            except:
                log.exception("pack: failed")
                conn.rollback()
                raise
            else:
                log.info("pack: finished successfully")
                conn.commit()
        finally:
            self.connmanager.close(conn, cursor)

    from relstorage.adapters.packundo import HistoryFreePackUndo
    @monkeypatch('relstorage.adapters.packundo.HistoryFreePackUndo')
    def _pack_cleanup(self, conn, cursor):
        # commit the work done so far
        conn.commit()
        self.locker.release_commit_lock(cursor)
        log.info("pack: cleaning up")

        # This section does not need to hold the commit lock, as it only
        # touches pack-specific tables. We already hold a pack lock for that.
        stmt = """
        DELETE FROM object_refs_added
        WHERE zoid IN (
            SELECT zoid
            FROM pack_object
            WHERE keep = %(FALSE)s
        );

        DELETE FROM object_ref
        WHERE zoid IN (
            SELECT zoid
            FROM pack_object
            WHERE keep = %(FALSE)s
        );

        DELETE FROM {0}
        WHERE zoid IN (
            SELECT zoid
            FROM pack_object
            WHERE keep = %(FALSE)s
        );

        DELETE FROM {0}
        WHERE zoid_from IN (
            SELECT zoid
            FROM pack_object
            WHERE keep = %(FALSE)s
        );

        %(TRUNCATE)s pack_object
        """.format(MONKEY_HELPER.TABLE_NAME)

        self.runner.run_script(cursor, stmt)

except ImportError:
    pass

