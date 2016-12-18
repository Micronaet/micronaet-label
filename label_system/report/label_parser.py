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
from openerp.osv import osv
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
    def load(self, record, field, mode='data', check_show=True, lang=False, 
            counter=-1):
        ''' Abstract function for load data in report
        
            record: browse pointer to job element with all record data in it
                The job will created from MRP process, in this case are read
                only but the operator could change the data put in "fast" mode
                the label for modify some field in it o re-print the less label
            
            field: name of the key field to get (end part of record_mode 
                syntax in database): record + mode + field
            
            mode: 3 value are possible: 
                data: return the data for the field passed
                string: return the label string text for the field passed
                print: return boolead for show or not show check
                All the field must be passed as the simple name, procedure
                append record + mode + field name for create field name present
                in record job
                NOTE: counter_pack_total is an ecception (field not in DB)
                
            check_show: means that if not present record_print_* whe record_data
                or record_string fill be leaved empty (so write nothing), 
                sometimes will be tested in record_print mode directly in the
                report
                
            lang: if present return field in data translation for language
            
            counter: used for counter_pack_total data if present
        '''
        empty = ''
        
        # Check mode passed:
        if mode not in ('data', 'print', 'string'):
            #_logger.error('Check mode in label, no value: print, string, data')
            raise osv.except_osv(
                _('Program error'), 
                _('Check mode in label, no value: print, string, data'),
                )
        
        # Test show depend on paramenter and other controls:
        if check_show and mode == 'data':
            show_field = 'record_print_%s' % field
            if show_field in record._columns:
                show = record.__getattribute__(show_field) == 'show'
            else:
                _logger.error(
                    'Show field not found: %s (assume yes)' % show_field)
                show = True            
        else:
            show = True
        if not show: 
            return empty
            
        # Generate field name:        
        field = 'record_%s_%s' % (mode, field)
        if field == 'record_data_counter_pack_total':                    
            # Manage counter here:
            if counter < 0:
                #_logger.error('Report error: counter passed without current')
                raise osv.except_osv(
                    _('Report error'), 
                    _('Report error: counter passed without current'),
                    )
            return '%s / %s' % (
                counter + 1, 
                record.record_data_counter, # Total record
                )
        elif field not in record._columns:
            #_logger.error('Field not present: %s' % field)
            raise osv.except_osv(
                _('Program error'), 
                _('Field not present: %s' % field),
                )        
        else: # Normal field:
            return record.__getattribute__(field)

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
        job_pool = self.pool.get('label.label.job')
        
        item_ids = data.get('record_ids', [])
        if not item_ids:
            _logger.error('No data for fast print')
            #raise osv.except_osv(
            #    _('Fast print'),
            #    _('No data for fast print'),
            #    )

        return [job for job in job_pool.browse(
            cr, uid, item_ids, context=context)] # for report loop:                
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
