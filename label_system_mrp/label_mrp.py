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
        partner_pool = self.pool.get('res.partner')
        note_pool = self.pool.get('note.note')
        
        mrp_proxy = self.browse(cr, uid, ids, context=context)[0]
        
        # Remove previous label:
        remove_ids = [item.id for item in mrp_proxy.label_job_ids]
        if remove_ids:
            job_pool.unlink(cr, uid, remove_ids, context=context)
            
        sequence = 0
        labels = ['article', 'package'] #'pallet', 'placeholder'
            
        for line in mrp_proxy.order_line_ids:
            for label in labels:
                sequence += 1
                
                # -------------------------------------------------------------
                # Search 3 label depend on note system management:
                # -------------------------------------------------------------
                # TODO generate label_id with system note management!
                label_id = note_pool.get_label_from_order_line(
                    cr, uid, line, label, context=context)
                report_id = False # TODO
                
                # -------------------------------------------------------------
                # Generate extra data from order, product, partner, address
                # -------------------------------------------------------------
                record_data = partner_pool.generate_job_data_from_line_partner(
                    cr, uid, line=line, context=context)
                # used for # label:
                q_x_pack = record_data.get('record_data_q_x_pack', False)
                
                if label == 'article':
                    record_data_counter = line.product_uom_qty
                else:
                    if q_x_pack: # TODO Manage Error:
                        record_data_counter = line.product_uom_qty / q_x_pack
                    else:    
                        record_data_counter = line.product_uom_qty
                        # XXX Note: q_x_pack Remain false in job
                
                # -------------------------------------------------------------
                # Create Job:            
                # -------------------------------------------------------------
                # Integrate with line information:
                record_data.update({
                    'sequence': sequence,
                    'label_id': label_id, # label.label
                    'report_id': report_id, #label.label.report
                    #'lang_id':,
                    'demo': False,
                    'fast': False,
                    
                    'record_data_counter': record_data_counter,

                    #'error': # TODO
                    #'comment_error' # TODO
                    })
                job_pool.create(cr, uid, record_data, context=context)
        return True
    
    def label_check_report(self, cr, uid, ids, context=None):
        ''' Report for check error label
        '''
        # TODO
        return True
        
    _columns = {
        'label_job_ids': fields.one2many(
            'label.label.job', 'mrp_id', 
            'Label Job'),
        }
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
