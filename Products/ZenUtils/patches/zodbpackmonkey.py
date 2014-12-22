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
    def pack(self, pack_tid, sleep=None, packed_func=None)
"""

from Products.ZenUtils.Utils import monkeypatch
from collections import defaultdict

import logging
import os
import pickle
import time

log = logging.getLogger("zenoss.zodbpack.monkey")

GLOBAL_OPTIONS = []

def set_build_tables_only_option():
    GLOBAL_OPTIONS.append("BUILD_TABLES_ONLY")

class ZodbPackMonkeyHelper(object):

    REF_TABLE_NAME = 'object_ref'
    REVERSE_REF_INDEX = 'reverse_ref_index'
    PICKLE_FILENAME = 'zodbpack_skipped_oids.pickle'
    ROLLBACK_OIDS_FILENAME = 'zodbpack_rollback_oids.txt'

    class ReferencesMap(object):
        def __init__(self):
            self.refs_to = defaultdict(set) # list of objects a specific oid references to
            self.refs_from = defaultdict(set) # list of objects that reference a specific oid

        def add_reference(self, ref, log=False):
            """
            @param ref: tuple (zoid, to_zoid)
            """
            oid, to_oid = ref
            self.refs_to[oid].add(to_oid)
            self.refs_from[to_oid].add(oid)

        def get_references(self, oid):
            """ returns objects that are at distance 1 from oid  """
            return self.refs_to[oid] | self.refs_from[oid]

    def create_reverse_ref_index(self, cursor):
        """
        Checks if the reverser reference index exists on the 
        reference table and creates the index if it does not exist
        """
        sql = """ SHOW INDEX FROM {0} WHERE key_name="{1}"; """.format(self.REF_TABLE_NAME, self.REVERSE_REF_INDEX)
        cursor.execute(sql)
        if cursor.rowcount == 0:
            log.info("Creating reverse reference index on {0}".format(self.REF_TABLE_NAME))
            start = time.time()
            index_sql = """ CREATE INDEX {0} ON {1} (to_zoid); """.format(self.REVERSE_REF_INDEX, self.REF_TABLE_NAME)
            cursor.execute(index_sql)
            log.info("Reverse reference index creation took {0} seconds.".format(time.time()-start))

    def get_current_database(self, cursor):
        sql = """SELECT DATABASE();"""
        cursor.execute(sql)
        return cursor.fetchall()[0][0]

    def delete_batch(self, cursor, batch):
        sql = """ DELETE FROM object_state WHERE zoid = %s AND tid = %s """
        count = cursor.executemany(sql, batch)
        return count

    def log_exception(self, e, info=''):
        log.error("Monkey patch for zodbpack raised and exception: {0}: {1}".format(info, e))

    def unmark_rolledback_oids(self, conn, cursor, oids):
        """
        Unmark the oids from pack_object so _pack_cleanup wont remove them from object_refs_added and object_ref
        """
        batch_size=10000
        to_remove = oids[:]
        while to_remove:
            batch = to_remove[:batch_size]
            del to_remove[:batch_size]
            values = ', '.join([ str(zoid) for zoid, tid in batch ])
            sql = """UPDATE pack_object SET keep = TRUE WHERE zoid IN ({0});""".format(values)
            cursor.execute(sql)
        conn.commit()

    def _get_references(self, cursor, batch):
        """
        @param batch: list of oids
        Returns all references where oid is in zoid or to_zoid
        """
        values = ','.join(str(zoid) for zoid, tid in batch)
        sql = """ SELECT zoid, to_zoid FROM {0} WHERE zoid!=to_zoid AND (zoid IN ({1}) OR to_zoid IN ({1}))""".format(self.REF_TABLE_NAME, values)
        cursor.execute(sql)
        result = cursor.fetchall()
        return result

    def _get_oid_references(self, cursor, oids):
        """
        Builds a 'ReferencesMap' containing all references from and to each oid in oids
        """
        references_map = ZodbPackMonkeyHelper.ReferencesMap()
        zoids = oids[:]
        batch_size = 10000
        n_batch = 1
        while zoids:
            start = time.time()
            batch = zoids[:batch_size]
            del zoids[:batch_size]
            references = self._get_references(cursor, batch)
            for r in references:
                references_map.add_reference(r)
            n_batch = n_batch + 1
        return references_map

    def _get_connected_oids_to(self, oid, references, visited):
        """ returns objects that are at distance 1 from oid and have not been already visited """
        objects = references.get_references(oid)
        return [ oid for oid in objects if visited.get(oid) is not None ]

    def _get_connected_oids(self, initial_oid, references, visited):
        """ breadth-first search to find all reachable oids from 'initial_oid' """
        connected_oids = []
        queue = {initial_oid}
        while queue:
            current_oid = queue.pop()
            del visited[current_oid]
            connected_oids.append(current_oid)
            queue.update(self._get_connected_oids_to(current_oid, references, visited))
        return connected_oids

    def group_oids(self, cursor, to_remove):
    	"""
    	Return a list of grouped oids. Each group represents oids that are part
    	of the same 'zenoss object'. All oids in a group have to be deleted in a
    	transactional way to avoid PKE (todos o ninguno)
    	"""
        references = self._get_oid_references(cursor, to_remove)
    	oids_to_remove = [ oid for (oid, tid) in to_remove ]
    	visited = { oid:False for oid in oids_to_remove }

        grouped_oids = []
        while visited:
            oid, vis = visited.popitem()
            visited[oid] = vis
            connected_oids = self._get_connected_oids(oid, references, visited)
            grouped_oids.append(connected_oids)
        oid_tid_mapping = dict(to_remove)
        oid_count = 0
        grouped_oids_with_tid = []
        for group in grouped_oids:
            oid_count = oid_count + len(group)
            group_with_tid = []
            for oid in group:
                group_with_tid.append((oid, oid_tid_mapping[oid]))
            grouped_oids_with_tid.append(group_with_tid)

        assert(oid_count==len(to_remove))

        return grouped_oids_with_tid

    def _get_count_in_table(self, cursor, oids_to_check, table_name, select_fields, where_fields):
        """ method to perform queries needed for tests """
        oids = list(oids_to_check)
        count = 0
        batch_size = 10000
        if isinstance(select_fields, list):
            select_fields = ", ".join(select_fields)
        if isinstance(where_fields, list):
            where_fields =  ", ".join(where_fields)
        while oids:
            batch = oids[:batch_size]
            del oids[:batch_size]
            values = ", ".join(batch)
            sql = """ SELECT COUNT({0}) FROM {1} WHERE {2} IN ({3});""".format(select_fields, table_name, where_fields, values)
            cursor.execute(sql)
            count = count + cursor.fetchall()[0][0]
        return count

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

        # Check tables state, deleted oids must not be in any of the tables and 
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
            batch_size=10000
            skipped = skipped_oids[:]
            object_state_data = []
            while skipped:
                batch = skipped[:batch_size]
                del skipped[:batch_size]
                values = ','.join( str(oid) for oid, tid in batch )
                sql = """SELECT zoid, tid FROM object_state WHERE zoid IN ({0})""".format(values)
                cursor.execute(sql)
                object_state_data.extend(cursor.fetchall())

            data = set(object_state_data) - set(skipped_oids)
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
        MONKEY_HELPER.create_reverse_ref_index(cursor)
        original(self, conn, cursor, pack_tid, get_references)

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

        explore_references_time = time.time() - group_start
        if explore_references_time > 1:
            explore_references_time = str(explore_references_time).split('.')[0]
            log.info("Exploring oid connections took {0} seconds.".format(explore_references_time))

        return grouped_oids

    from relstorage.adapters.packundo import HistoryFreePackUndo
    @monkeypatch('relstorage.adapters.packundo.HistoryFreePackUndo')
    def remove_isolated_oids(self, conn, cursor, grouped_oids, sleep, packed_func, total, oids_processed):
        """
        objects that not connected to other objects can be safely removed.
        """
        # We'll report on progress in at most .1% step increments
        reportstep = max(total / 1000, 1)
        if oids_processed == 0:
            lastreport = 0
        else:
            lastreport = oids_processed / reportstep * reportstep

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
                counter = oids_processed
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
        if oids_processed == 0:
            lastreport = 0
        else:
            lastreport = oids_processed / reportstep * reportstep

        batch_size = 1000 # some batches can be huge and we are holding the commit lock
        prevent_pke_oids = [] # oids that have not been deleted to prevent pkes
        rollbacks = 0
        self._pause_pack_until_lock(cursor, sleep)
        start = time.time()
        for oids_group in grouped_oids:
            if len (oids_group) == 1:
                # isolated oids are processed by other method
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
                counter = oids_processed
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
            MONKEY_HELPER.unmark_rolledback_oids(conn, cursor, prevent_pke_oids)
            try:
                MONKEY_HELPER.export_rolledback_oids(cursor, prevent_pke_oids)
            except Exception as e:
                MONKEY_HELPER.log_exception(e, "Exception while exporting skipped oids.")

        return prevent_pke_oids
            
    from relstorage.adapters.packundo import HistoryFreePackUndo
    @monkeypatch('relstorage.adapters.packundo.HistoryFreePackUndo')
    def pack(self, pack_tid, sleep=None, packed_func=None):
        """ Run garbage collection. Requires the information provided by pre_pack. """

        if "BUILD_TABLES_ONLY" in GLOBAL_OPTIONS:
            log.info("pack: Skipping pack phase.")
            return

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
                    log.info("Grouping connected oids... (may take a while)")
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

except ImportError:
    pass
