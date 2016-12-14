# -*- coding: utf-8 -*-
###############################################################################
#
#    Copyright (C) 2001-2014 Micronaet SRL (<http://www.micronaet.it>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published
#    by the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
###############################################################################
import os
import sys
import logging
import openerp
import openerp.netsvc as netsvc
import openerp.addons.decimal_precision as dp
from openerp.osv import fields, osv, expression, orm
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from openerp import SUPERUSER_ID, api
from openerp import tools
from openerp.tools.translate import _
from openerp.tools.float_utils import float_round as round
from openerp.tools import (DEFAULT_SERVER_DATE_FORMAT, 
    DEFAULT_SERVER_DATETIME_FORMAT, 
    DATETIME_FORMATS_MAP, 
    float_compare)


_logger = logging.getLogger(__name__)

class MrpProduction(orm.Model):
    """ Model name: MrpProduction
    """
    
    _inherit = 'mrp.production'
    
    def generate_label_job(self, cr, uid, ids, context=None):
        ''' Generate list of jobs label
        '''
        assert len(ids) == 1, 'Works only with one record a time'
        
        # Pool used:
        job_pool = self.pool.get('label.label.job')
        
        mrp_proxy = self.browse(cr, uid, ids, context=context)[0]
        
        # Remove previous label:
        remove_ids = [item.id for item in mrp_proxy.label_job_ids]
        if remove_ids:
            job_pool.unlink(cr, uid, remove_ids, context=context)
            
        sequence = 0
        labels = [
            'article',
            'pack',
            #('pallet', ),
            ]
        for line in mrp_proxy.order_line_ids:
            for label in labels:
                sequence += 1
                q_x_pack = line.product_id.q_x_pack
                
                # -----------------------------------------------------------------
                # Search 3 label depend on note system management:
                # -----------------------------------------------------------------
                # TODO loop for 3 label schema
                report_id = False # TODO
                label_id = 1 # TODO
                
                if label == 'article':
                    record_counter = line.product_uom_qty
                else:
                    if not q_x_pack:
                        # XXX Manage Error:
                        q_x_pack = 1
                    record_counter = line.product_uom_qty / q_x_pack
                
                # -----------------------------------------------------------------
                # Create Job:            
                # -----------------------------------------------------------------
                job_pool.create(cr, uid, {
                    'sequence': sequence,
                    'label_id': label_id, # label.label
                    'report_id': report_id, #label.label.report
                    #'lang_id':,
                    'demo': False,
                    'fast': False,
                    
                    'product_id': line.product_id.id,
                    'partner_id': line.order_id.partner_id.id,
                    'address_id': line.order_id.destination_partner_id,
                    'order_id': line.order_id.id,
                    'line_id': line.id,
                    'mrp_id': mrp_proxy.id,

                    #'error': # TODO
                    #'comment_error' # TODO
                    'record_counter': record_counter,        
                    #'record_name': 
                    #'record_customer_name': 
                    #'record_frame': 
                    #'record_color': 
                    #'record_fabric': 
                    #'record_code': 
                    #'record_customer_code': 
                    #'record_ean13':
                    #'record_ean8': 
                    'record_q_x_pack': q_x_pack,
                    #'record_static_text1':
                    #'record_static_text2':
                    #'record_static_text3':
            
                    #'record_line':
                    #'record_period':
                    #'record_order_ref':
                    #'record_order_date':
                    #'record_counter_pack_total':
                    }, context=context)
        return True
    
    _columns = {
        'label_job_ids': fields.one2many(
            'label.label.job', 'mrp_id', 
            'Label Job'),
        }
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
