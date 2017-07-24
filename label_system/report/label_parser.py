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
from openerp.report import report_sxw
from openerp.report.report_sxw import rml_parse

# XXX problem during import procedure:
#import openerp
#import openerp.netsvc as netsvc
#import openerp.addons.decimal_precision as dp
#from openerp.osv import fields, osv, expression, orm
#from datetime import datetime, timedelta
#from openerp import SUPERUSER_ID#, api
#from openerp import tools
#from datetime import datetime, timedelta
#from openerp.tools.translate import _

_logger = logging.getLogger(__name__)

class Parser(report_sxw.rml_parse):
    # Constructor
    def __init__(self, cr, uid, name, context):
        super(Parser, self).__init__(cr, uid, name, context)
        self.localcontext.update({
            'get_report_label': self.get_report_label,
            'get_placeholder': self.get_placeholder,
            #'get_report_placeholder': self.get_report_placeholder,
            'load': self.load,
            'date_reformat': self.date_reformat,
            # TODO load_image function for extra image        
        })

    def date_reformat(self, date_iso, date_format='it', separator='/'):
        ''' Return ISO date in format
            date_format: 
                'it': 'GG/MM/AA'
                'IT': 'GG/MM/AA'
                # TODO 
        '''
        if not date_iso:
            return ''
        if date_format == 'it': 
            return '%s%s%s%s%s' % (
                date_iso[8:10],
                separator,
                date_iso[5:7],
                separator,
                date_iso[2:4],
                )
        if date_format == 'IT': 
            return '%s%s%s%s%s' % (
                date_iso[8:10],
                separator,
                date_iso[5:7],
                separator,
                date_iso[:4],
                )
        else:
            _logger.error('No format passed or managed %s!' % date_format)
            return date_iso
                
    def get_placeholder(self, data, field=False):
        ''' Get placeholder if present
        '''
        ph = data.get('placeholder_data', False)
        if not ph:
            return False
        if not field:
            return True # ph present
        return data['placeholder_data'].get(field, '')
        
    # Method for local context
    def load(self, record, field, mode='data', check_show=True, lang=False, 
            counter=-1, position=0):
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
                
            check_show: means that if not present record_print_* when
                record_data or record_string fill be leaved empty
                (so write nothing), 
                sometimes will be tested in record_print mode directly in the
                report
                
            lang: if present return field in data translation for language
            
            counter: used for counter_pack_total data if present
            
            position: if setted in sting mode split vaue with | and take
                position element
        '''
        empty = ''

        # Check mode passed:
        if mode not in ('data', 'print', 'string'):
            #_logger.error('Check mode in label, no value: print,string,data')
            raise osv.except_osv(
                _('Program error'), 
                _('Check mode in label, no value: print, string, data'),
                )
        
        # Test show depend on paramenter and other controls:
        if check_show and mode in ('data', 'string'): #TODO don't check counter
            show_field = 'record_print_%s' % field
            if show_field in record._columns:
                show = record.__getattribute__(show_field)
            else:
                _logger.error(
                    'Show field not found: %s (assume yes)' % show_field)
                show = True # for not present fields           
        else:
            show = True
        if not show: 
            return empty
        
        # ---------------------------------------------------------------------    
        # Generate field name:
        # ---------------------------------------------------------------------    
        field_name = 'record_%s_%s' % (mode, field)
        
        # Counters
        if field_name == 'record_data_counter_pack_total':                    
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
        
        # Logo and images:        
        elif field in ('company_logo', 'partner_logo', 'linedrawing'):
            # TODO manage better
            # Return image:
            if field == 'company_logo':
                return record.partner_id.company_id.partner_id.label_image
            elif field == 'partner_logo':
                return record.partner_id.label_image
            elif field == 'linedrawing':
                return record.product_id.wireframe
            else:
                return ''
        
        # Field not present:        
        elif field_name not in record._columns:
            _logger.error('Field not present: %s' % field_name)
            # TODO for partner_code raise error but not present!
            #raise osv.except_osv(
            #    ('Program error'), 
            #    ('Field not present: %s' % field_name),
            #    )      
                  
        # Field (normale data)          
        else:
            # String use | separator for split article|pack|pallet
            if mode == 'string':
                string = record.__getattribute__(field_name).split('|')
                if position >= len(string):
                    _logger.info('Position > len split string')
                    position = 0
                return string[position] or ''
            else:   
                return record.__getattribute__(field_name)

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
        
        return job_pool.browse(cr, uid, item_ids, context=context)
            
    """def get_report_placeholder(self, data=None):
        ''' Master function for generate label elements
            data:
                report_data: test, fast, production are the current value
        '''
        # TODO assert 1?
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
        
        job_proxy = job_pool.browse(cr, uid, item_ids, context=context)[0]
        line = job_proxy.line_id

        if line:
            res = ((
                line.product_id.default_code or '???',
                line.order_id.partner_id.name or '',
                line.order_id.destination_partner_id.name or '',
                line.order_id.name or '',
                job_proxy.record_data_counter or '',
                job_proxy.record_data_line or '',
                job_proxy.record_data_period or '',                
                ), )
        else:
            res = (('', '', '', '', '', '', ''), )
        return res"""
            
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
