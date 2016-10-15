#!/usr/bin/python
# -*- coding: utf-8 -*-
##############################################################################
#
#   Copyright (C) 2010-2012 Associazione OpenERP Italia
#   (<http://www.openerp-italia.org>).
#   Copyright(c)2008-2010 SIA "KN dati".(http://kndati.lv) All Rights Reserved.
#                   General contacts <info@kndati.lv>
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU Affero General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU Affero General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
import os
import sys
import logging
#import openerp
#import openerp.netsvc as netsvc
#import openerp.addons.decimal_precision as dp
#from openerp.osv import fields, osv, expression, orm
#from datetime import datetime, timedelta
#from openerp import SUPERUSER_ID#, api
#from openerp import tools
from openerp.report import report_sxw
from openerp.report.report_sxw import rml_parse
#from datetime import datetime, timedelta
#from openerp.tools.translate import _


_logger = logging.getLogger(__name__)

class Parser(report_sxw.rml_parse):
    # Constructor
    def __init__(self, cr, uid, name, context):
        super(Parser, self).__init__(cr, uid, name, context)
        self.localcontext.update({
            'get_report_label': self.get_report_label,
            'load': self.load,
        })

    # Method for local context
    def load(self, record, field, mandatory=False, empty='', error='ERR'):
        ''' Abstract function for load data in report
        '''
        if field in record:
            res = record[field]
            if mandatory and not res:
                _logger.error('Empty mandatory field %s' % field)
                return error
            elif res:
                return res
            else:
                _logger.warning('Empty field %s' % field)
                return empty
        else:
            if mandatory:
                _logger.error(
                    'Field %s not present in record structure' % field)
                return error
            else:
                _logger.warning(
                    'Field %s not present in record structure' % field)
                return empty

    def get_report_label(self, data=None):
        ''' Master function for generate label elements
            data:
                report_data: test, fast, production are the current value
        '''
        if data is None:
            data = {}

        # Standard:
        cr = self.cr
        uid = self.uid
        context = {}
        
        # Pool used:
        label_pool = self.pool.get('label.label')        
        fast_pool = self.pool.get('label.label.job')
        
        item_ids = data.get('record_ids', [])
        if not item_ids:
            raise osv.except_osv(
                _('Fast print'),
                _('No data for fast print'),
                )

        records = [] # for report loop:                
        for job in fast_pool.browse(cr, uid, item_ids, context=context):
            # TODO manage counter progr.
            record = {}
            for field in label_pool._columns.keys():
                if not field.startswith('record_'):
                    continue # jump field
                record[field[7:]] = job.__getattribute__(field) or ''
            records.append(record)
        return records
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
