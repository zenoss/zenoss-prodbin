###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2010, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################
from sqlalchemy import select, case, Integer, Column
from sqlalchemy.orm import MapperExtension, aliased
from sqlalchemy.sql import and_, or_
from zope.interface import implements
from Products.ZenUtils.orm.meta import Session

object_session = Session.object_session

from .interfaces import IMultiTreeNestedSetMember

class MultiTreeNestedSetExtension(MapperExtension):
    def before_insert(self, mapper, connection, instance):
        if not instance.parent:
            instance.left = 1
            instance.right = 2
        else:
            tbl = mapper.mapped_table
            right_most_sibling = connection.scalar(
                select([tbl.c.rgt]).where(and_(tbl.c.id==instance.parent.id,
                                               tbl.c.category==instance.parent.category))
            )
            connection.execute(
                tbl.update(tbl.c.rgt>=right_most_sibling).values(
                    lft = case(
                        [(tbl.c.lft>right_most_sibling, tbl.c.lft + 2)],
                        else_ = tbl.c.lft
                    ),
                    rgt = case(
                        [(tbl.c.rgt>=right_most_sibling, tbl.c.rgt + 2)],
                        else_ = tbl.c.rgt
                    )
                ).where(tbl.c.category==instance.category)
            )
            instance.left = right_most_sibling
            instance.right = right_most_sibling + 1

    def after_delete(self, mapper, connection, instance):
        tbl = mapper.mapped_table
        # Delete the subtree
        connection.execute(
            tbl.delete(
                and_(tbl.c.lft.between(instance.left, instance.right),
                     tbl.c.category==instance.category)
            )
        )
        # Close the gaps
        connection.execute(
            tbl.update(
                and_(
                    tbl.c.category==instance.category,
                    or_(
                        tbl.c.lft>instance.left,
                        tbl.c.rgt>instance.left)
                )
            ).values(
                lft = case(
                    [(tbl.c.lft>instance.left,
                      tbl.c.lft - (instance.right - instance.left + 1))],
                    else_ = tbl.c.lft
                ),
                rgt = case(
                    [(tbl.c.rgt>instance.left,
                      tbl.c.rgt - (instance.right - instance.left + 1))],
                    else_ = tbl.c.rgt
                )
            )
        )


class MultiTreeNestedSetItem(object):
    """
    Mixin for a declarative base.
    """
    implements(IMultiTreeNestedSetMember)
    __mapper_args__ = {
        'extension': MultiTreeNestedSetExtension(),
        'batch': False
    }
    parent = None
    # Composite primary key (id, category)
    # An item can be n trees 0 or 1 times
    id = Column(Integer, primary_key=True, nullable=False)
    category = Column(Integer, primary_key=True, nullable=False)
    left = Column("lft", Integer, nullable=False)
    right = Column("rgt", Integer, nullable=False)

    def parents(self):
        tbl = self.__class__
        alias = aliased(tbl)
        query = object_session(self).query(self.__class__)
        return query.filter(alias.left.between(tbl.left, tbl.right))\
                    .filter(alias.id==self.id).filter(
                        and_(
                            alias.category==self.category,
                            tbl.category==self.category
                        )
                    )

