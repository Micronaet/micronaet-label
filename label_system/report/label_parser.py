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
#import logging
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

#_logger = logging.getLogger(__name__)

class Parser(report_sxw.rml_parse):
    
    # Constructor
    def __init__(self, cr, uid, name, context):        
        super(Parser, self).__init__(cr, uid, name, context)
        self.localcontext.update({
            'get_report_label': self.get_report_label,
        })
    
    # Method for local context    
    def get_report_label(self, data=None):
        ''' Master function for generate label elements
            data:
                report_data: test, fast, production are the current value                
        '''
        if data is None:
            data = {}
        
        # Standar:
        cr = self.cr
        uid = self.uid
        context = {]
        
        report_data = data.get('report_data', 'test')

        field_list = [ # XXX schemd for check, not used for now
            # -----------------------------------------------------------------
            #                      Label report:
            # -----------------------------------------------------------------
            'counter', # number of label
            'multi', # number of label per page
            'lang',                    
            # -----------------------------------------------------------------
            # Product data:
            # -----------------------------------------------------------------
            # Description:
            'name', 'customer_name',
            'frame', 'color', 'canvas', 
            # Code:
            'code', 'customer_code', 'codebar', 
            # Extra:            
            'q_x_pack',             
            # Static:
            'static_text1', 'static_text2', 'static_text3',            
            # -----------------------------------------------------------------
            # Production:
            # -----------------------------------------------------------------
            # Line:
            'line', 'period', 
            # Order:
            'order_ref', 'order_data',
            # Counter:
            'counter_pack', # 1 of 25 (reset every product)            
            # -----------------------------------------------------------------
            # Logo:
            # -----------------------------------------------------------------
            # Logo Image:
            'company_logo', 'customer_logo', 'recycle',
            # Picture image:
            'image', 'drawing',
            ]
        
        data = [] # for report loop:
        if report_data == 'test':
            record = {
                'counter': 3, # test 3 record
                'name': 'Product name',
                'code': 'Code',
                'codebar': '8032615811506', # if not hide
                'frame': 'Frame element',
                'color': 'Color product',                
                }  
            data.append(record)              
            
        elif report_data == 'fast':
            item_ids = data.get('record_ids', [])
            if not item_ids:
                raise osv.except_osv(
                    _('Fast print'), 
                    _('No data for fast print'),
                    )
            # Generate list of label:
            fast_pool = self.pool.get('label.label.fast')
            for fast in fast_pool.browse(cr, uid, item_ids, context=context):
                # TODO manage counter progr.
                record = {
                    'counter': fast.counter or 1, # test 3 record
                    #'multi',
                    #'lang',
                    'name': fast.force_name or fast.product_id.name or '?', 
                    'customer_name': '?', # TODO
                    'frame': fast.force_frame, 
                    'color': fast.force_color, 
                    'canvas': fast.force_canvas, 
                    'code': 
                        fast.force_code or fast.product_id.default_code or '', 
                    'customer_code': '?', # TODO 
                    'codebar': 
                        fast.force_codebar or fast.product_id.ean13 or '', 
                    'q_x_pack': fast.q_x_pack or fast.product_id.q_x_pack,
                    'static_text1': fast.static_text1, 
                    'static_text2': fast.static_text2, 
                    'static_text3': fast.static_text3,
                    'line': fast.line or '', 
                    'period': fast.period or '', 
                    'order_ref': fast.order_ref or '',
                    'order_data': fast.order_data or '',
                    'counter_pack': '', # 1 of 25 (reset every product) TODO
                    # TODO image:
                    'company_logo': False, 
                    'customer_logo': False, 
                    'recycle': False,
                    'image': False, 
                    'drawing': False,
                    }
                data.append(record)    
            
        elif report_data == 'production':
            pass
            
        else:
            raise osv.except_osv(
                _('Error data'), 
                _('Report data mode not found: %s' % report_data),
                )        
        return data
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
