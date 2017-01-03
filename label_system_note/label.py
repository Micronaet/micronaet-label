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

class NoteType(orm.Model):
    """ Model name: NoteType
    """    
    _inherit = 'note.type'
    
    _columns = {
        'print_label': fields.boolean('Label type'),
        'label_category': fields.selection([
            ('article', 'Article'),
            ('package', 'Package'),
            ], 'Label category'),
        }
    
    _defaults = {    
        'label_category': lambda *x: 'article',
        }

class NoteNote(orm.Model):
    """ Model name: NoteNote
    """    
    _inherit = 'note.note'
    
    def get_label_from_order_line(self, cr, uid, line, context=None):
        ''' Read line and explode other data, search label and return better
            priority
        '''
        product_pool = self.pool.get('product.product')
        
        if not line:
            raise osv.except_osv(
                _('Label generation'), 
                _('Error no line selected, cannot choose label'),
                )
                
        # Create extra filter from line:
        product = line.product_id # mandatory
        partner = line.order_id.partner_id # mandatory
        address = line.order_id.destination_partner_id # optional
        order = line.order_id # mandatory
        #line mandatory
        
        # TODO filter category selected
        
        # 1. Search partner label:
        label_ids = set(self.search(cr, uid, [
            ('print_label', '=', True),
            ('partner_id', '=', partner.id),
            ], context=context))
            
        # 2. Search address label:
        if address:
            label_ids.update(set(self.search(cr, uid, [
                ('print_label', '=', True),
                ], context=context)))
                
        # 3. Search product no customer (so no address)
        label_ids.update(set(self.search(cr, uid, [
            ('print_label', '=', True),
            ('product_id', '=', product.id),
            ('partner_id', '=', False),
            ], context=context)))
            
        # 4. Search order
        label_ids.update(set(self.search(cr, uid, [
            ('print_label', '=', True),
            ('order_id', '=', order.id),
            ], context=context)))
            
        # 5. Search line    
        label_ids.update(set(self.search(cr, uid, [
            ('print_label', '=', True),
            ('line_id', '=', line.id),
            ], context=context)))
            
        if not label_ids:
            return False
                
        label_proxy = self.browse(cr, uid, list(label_ids), context=context)
        labels = sorted(
            label_proxy, 
            key=lambda l: product_pool.get_note_priority(
                l.product_id.id, 
                l.partner_id.id,
                l.address_id.id,
                l.order_id.id,
                l.line_id.id,
                )
            )
        # TODO manage label not required
        return labels[-1].label_id.id
        
    _columns = {
        'print_label': fields.boolean('Label note'),
        'print_not_required': fields.boolean('Label not required'),
        'label_id': fields.many2one('label.label', 'Label'),
        }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
