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
        #'label_category': lambda *x: 'article',
        }
        
    #TODO _sql_constraints = [(
    #    'label_category_uniq', 'unique (label_category)', 
    #    'Label category must be unique in all category!',
    #    ),        
    #    ]    

class NoteNote(orm.Model):
    """ Model name: NoteNote
    """    
    _inherit = 'note.note'

    # -------------------------------------------------------------------------    
    # Utility:
    # -------------------------------------------------------------------------    
    def search_label_presence(self, cr, uid, domain, category, 
            context=None):
        ''' Search if label is present else return nothing
        '''
        domain.extend([
            ('print_label', '=', True),            
            ('type_id.label_category', '=', category),
            ])
        label_ids = self.search(cr, uid, domain, context=context)            
        if label_ids:
            if len(label_ids) > 1:
                _logger.error('More than one label!') # do nothing
            return self.browse(
                cr, uid, label_ids, context=context)[0].label_id.id
        return False

    def get_label_from_order_line(self, cr, uid, line, category, context=None):
        ''' Read line and explode other data, search label and return better
            priority
        '''
        import pdb; pdb.set_trace()
        if not line or not category:
            raise osv.except_osv(
                _('Label generation'), 
                _('Error no line selected or no category, so no label!'),
                )

        # ---------------------------------------------------------------------
        # Create extra filter from line:
        # ---------------------------------------------------------------------
        product = line.product_id # mandatory
        partner = line.order_id.partner_id # mandatory
        address = line.order_id.destination_partner_id # optional
        order = line.order_id # mandatory
        #line mandatory

        # ---------------------------------------------------------------------        
        # Search label form highest priority to lower:
        # ---------------------------------------------------------------------
        # ---------------
        # Order and line:
        # ---------------
        # 1. Search sale order line label
        label_id = self.search_label_presence(cr, uid, [
            ('line_id', '=', line.id),
            ], category, context=None)
        if label_id:
            return label_id

        # 2. Search order label
        label_id = self.search_label_presence(cr, uid, [
            ('order_id', '=', order.id),
            ('line_id', '=', False), # no line particularity
            ], category, context=context)
        if label_id:
            return label_id

        # ----------------
        # Address present:
        # ----------------
        if address:
            # 3A. Search product with address
            label_id = self.search_label_presence(cr, uid, [
                ('product_id', '=', product.id),
                #('partner_id', '=', address.id),
                ('address_id', '=', address.id),
                ('order_id', '=', False),
                ('line_id', '=', False),            
                ], category, context=context)
            if label_id:
                return label_id

            # 3B. Search address
            label_id = self.search_label_presence(cr, uid, [
                #('partner_id', '=', address.id),
                ('address_id', '=', address.id),
                ('product_id', '=', False),
                ('order_id', '=', False),
                ('line_id', '=', False),            
                ], category, context=context)
            if label_id:
                return label_id

        # ---------------
        # Partner search:
        # ---------------
        # 4A. Search product with partner
        label_id = self.search_label_presence(cr, uid, [
            ('product_id', '=', product.id),
            ('partner_id', '=', partner.id),
            ('address_id', '=', False),
            ('order_id', '=', False),
            ('line_id', '=', False),            
            ], category, context=context)
        if label_id:
            return label_id

        # 4B. Search partner
        label_id = self.search_label_presence(cr, uid, [
            ('partner_id', '=', partner.id),
            ('product_id', '=', False),
            ('address_id', '=', False),
            ('order_id', '=', False),
            ('line_id', '=', False),            
            ], category, context=context)
        if label_id:
            return label_id

        # ---------------
        # Product search:
        # ---------------
        # 5. Search product label:
        label_id = self.search_label_presence(cr, uid, [
            ('product_id', '=', product.id),
            ('partner_id', '=', False),
            ('address_id', '=', False),
            ('order_id', '=', False),
            ('line_id', '=', False),            
            ], category, context=context)
        if label_id:
            return label_id
        
        # ---------------
        # Company search:
        # ---------------
        company_id = partner.company_id.partner_id.id   
        # 6A. Search company label with product:
        label_id = self.search_label_presence(cr, uid, [
            ('product_id', '=', product.id),
            ('partner_id', '=', company_id),
            ('address_id', '=', False),
            ('order_id', '=', False),
            ('line_id', '=', False),            
            ], category, context=context)
        if label_id:
            return label_id

        # 6B. Search company label with product:
        label_id = self.search_label_presence(cr, uid, [
            ('product_id', '=', False),
            ('partner_id', '=', company_id),
            ('address_id', '=', False),
            ('order_id', '=', False),
            ('line_id', '=', False),            
            ], category, context=context)
        if label_id:
            return label_id

        _logger.error('No label found!')
        return False # raise error    
        
    _columns = {
        'print_label': fields.boolean('Label note'),
        'print_not_required': fields.boolean('Label not required'),
        'label_id': fields.many2one('label.label', 'Label'),
        }
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
