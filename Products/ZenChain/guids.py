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
from zope.component import adapter
from sqlalchemy import Integer, Column, types
from Products.ZenUtils.orm import meta, nested_transaction
from Products.ZenUtils.guid.interfaces import IGloballyIdentifiable
from Products.ZenUtils.guid.interfaces import IGUIDEvent


class Guid(meta.Base):
    __tablename__="guids"
    id = Column(Integer, primary_key=True)
    guid = Column(types.CHAR(length=36), nullable=False)


@adapter(IGloballyIdentifiable, IGUIDEvent)
def updateTableOnGuidEvent(object, event):
    old, new = event.old, event.new
    if new is None:
        # Deletion of guid
        with nested_transaction() as session:
            result = session.query(Guid).filter(Guid.guid==old).all()
            if result:
                for item in result:
                    session.delete(item)
    elif old is None:
        # Brand-new guid
        with nested_transaction() as session:
            session.add_all([Guid(guid=new)])
    else:
        # Somehow a guid changed. 
        with nested_transaction() as session:
            olds = session.query(Guid).filter(Guid.guid==old).all()
            if olds:
                for old in olds:
                    old.guid = new
            else:
                session.add_all([Guid(guid=new)])
