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

class ResPartnerProductParticLabel(orm.Model):
    """ Model name: ResPartnerProductParticLabel
    """
    
    _name = 'res.partner.product.partic.label'
    _description = 'Label partic'
    
    _columns = {
        'name': fields.selection([        
            ('frame', 'Frame'),
            ('fabric', 'Fabric'),
            #('color', 'Color'), # TODO ???
            ('static_text1', 'Text 1'),
            ('static_text2', 'Text 2'),
            ('static_text3', 'Text 3'),
            ], 'Field', required=True),
        'value': fields.text(
            'Value', required=True) , 
        'partic_id': fields.many2one('res.partner.product.partic', 'Partic'),    
        }        
    
class ResPartnerProductPartic(orm.Model):
    ''' Add product partic obj
    '''    
    _inherit = 'res.partner.product.partic'
    
    _columns = {
        # Customer code:
        'ean13': fields.char('EAN 13', size=13),
        'ean8': fields.char('EAN 8', size=8),
        'partner_pricelist': fields.float('Partner pricelist', digits=(16, 3)), 
    
        # Image fields:
        'label_field_ids': fields.one2many(
            'res.partner.product.partic.label', 'partic_id', 
            'Label field'),
        }

# TODO mode in a new module?
class ProductProduct(orm.Model):
    ''' Add product partic obj
    '''    
    _inherit = 'product.product'

    _columns = { 
        'ean8': fields.char('EAN 8', size=8),
        'q_x_pallet': fields.integer('Q. per pallet'),
        }

class NoteImage(orm.Model):
    ''' Add product partic obj
    '''    
    _inherit = 'note.image'
    
    _columns = {
        'label_image': fields.boolean('Image for label'),
        'label_code': fields.char('Label code', size=15,
            help='Code used for refer image in ODT files'),
        }
        
    _sql_constraints = [(
        'label_code_uniq', 'unique(label_code)', 
        'The label code must be unique!'), ]

class ResPartner(orm.Model):
    ''' Add product partic obj
    '''    
    _inherit = 'res.partner'
    
    def generate_job_data_from_line_partner(self, cr, uid, 
            **parameter):
        ''' Generate record for create printing jobs
            Parameter >> Dict for not mandatory paremeters, list below:
            
            line: used for generate all parameter, instead read passed (*_id)
            product_id: ID of product
            partner_id: ID of partner
            address_id: ID of address
            order_id: ID of order
            mrp_id: ID of MRP
            context: dict of extra parameter
        '''
        # ---------------------------------------------------------------------
        # Read parameters:
        # ---------------------------------------------------------------------
        context = parameter.get('context', {})
        line = parameter.get('line', False)
        
        # Pool used:
        product_pool = self.pool.get('product.product')
        partner_pool = self.pool.get('res.partner') # and address
        order_pool = self.pool.get('sale.order')
        mrp_pool = self.pool.get('mrp.production')
        
        # ---------------------------------------------------------------------
        # Header many2one data:
        # ---------------------------------------------------------------------
        if line:
            # Create browse obj for readability:
            product = line.product_id
            partner = line.order_id.partner_id
            address = line.order_id.destination_partner_id
            order = line.order_id
            mrp = line.mrp_id

            # Create record of m2o                
            res = {
                'product_id': product.id,
                'partner_id': partner.id,
                'address_id': address.id,
                'order_id': order.id,
                'line_id': line.id,
                'mrp_id': mrp.id,
                }
        else:
            # Get ID from parameters:
            product_id = parameter.get('product_id', False)
            partner_id = parameter.get('partner_id', False)
            address_id = parameter.get('address_id', False)
            order_id = parameter.get('order_id', False)
            mrp_id = parameter.get('mrp_id', False)
            
            # Check mandatory ID:
            if not product_id:
                # Mandatory element, raise error
                pass # TODO

            # Create record of m2o                
            res = {
                'product_id': product_id,
                'partner_id': partner_id,
                'address_id': address_id,
                'order_id': order_id,
                'line_id': False,
                'mrp_id': mrp_id,
                }
                
            # Browse record if present:
            # TODO check if present ID instead raise error (no data for label)            
            product = product_pool.browse(
                cr, uid, product_id, context=context)
            partner = partner_pool.browse(
                cr, uid, partner_id, context=context)
            address = partner_pool.browse(
                cr, uid, address_id, context=context)
            order = order_pool.browse(
                cr, uid, order_id, context=context)
            mrp = mrp_pool.browse(
                cr, uid, mrp_id, context=context)
                
        
        # ---------------------------------------------------------------------
        # Check parameter in partner form:
        # ---------------------------------------------------------------------
        
        
        
        # ---------------------------------------------------------------------
        # Product fields:
        # ---------------------------------------------------------------------
        res.update({        
                'record_name': product.name,
                #'record_customer_name': 
                #'record_frame': 
                #'record_color': 
                #'record_fabric': 
                'record_code': product.default_code,
                #'record_customer_code': 
                'record_ean13': product.ean13,
                'record_ean8': product.ean8,
                #'record_static_text1':
                #'record_static_text2':
                #'record_static_text3':            
                #'record_line':
                #'record_period':
                #'record_order_ref':
                #'record_order_date':
                #'record_counter_pack_total':
                })
            
        return res
        

    _columns = { 
        # ---------------------------------------------------------------------
        #                      EXTRA LANGUAGE ELEMENTS:
        # ---------------------------------------------------------------------
        #'label_lang_code': fields.char(
        #    'Print company code', 
        #    size=40, help='Extra lang code, use format: EN|DE|FR|IT'),
        'label_lang_description': fields.char(
            'Lang for description', 
            size=40, help='Extra lang descrition, use format: EN|DE|FR|IT'),
        'label_lang_frame': fields.char('Lang for frame',
            size=40, help='Extra lang frame, use format: EN|DE|FR|IT'),
        'label_lang_fabric': fields.char('Label for fabric', 
            size=40, help='Extra lang fabric, use format: EN|DE|FR|IT'), 
        #'label_lang_color': fields.char('Lang for color', 
        #    size=40, help='Extra lang code, use format: EN|DE|FR|IT'), 

        # ---------------------------------------------------------------------
        #                      LABEL STRING FOR ALL ELEMENTS:
        # ---------------------------------------------------------------------
        # Anagrafic text:
        'label_string_code': fields.char(
            'Print company code', 
            size=40, translate=True),
        'label_string_code_partner': fields.char('Print partner code', 
            size=40, translate=True),
        'label_string_description': fields.char(
            'Print company description', 
            size=40, translate=True),
        'label_string_description_partner': fields.char(
            'Print partner description', 
            size=40, translate=True),
        'label_string_frame': fields.char('Print frame',
            size=40, translate=True),
        'label_string_fabric': fields.char('Print fabric', 
            size=40, translate=True),

        # Anagrafic numeric:        
        'label_string_q_x_pack': fields.char('Print Q. x pack', 
            size=40, translate=True),
        'label_string_q_x_pallet': fields.char('Print Q. x pallet', 
            size=40, translate=True),
        'label_string_dimension': fields.char('Print dimension', 
            size=40, translate=True),
        'label_string_volume': fields.char('Print volume', 
            size=40, translate=True),
        'label_string_weight_net': fields.char('Print weight net', 
            size=40, translate=True),
        'label_string_weight_lord': fields.char('Print weight lord', 
            size=40, translate=True),
        'label_string_parcel': fields.char('Print parcel', 
            size=40, translate=True),
        'label_string_price': fields.char('Print price', 
            size=40, translate=True),
        #'label_string_price_uom':

        # EAN data:
        #'label_string_ean13' 'label_string_ean8'
        
        # Production:
        'label_string_line': fields.char('Print production line', 
            size=40, translate=True),
        'label_string_period': fields.char('Print period', 
            size=40, translate=True),
        'label_string_lot': fields.char('Print lot', 
            size=40, translate=True),
        
        # Order:
        'label_string_order_ref': fields.char('Print order ref', 
            size=40, translate=True), # customer
        'label_string_order_date': fields.char('Print order date', 
            size=40, translate=True),
        'label_string_destination_code': fields.char(
            'Print destination code', 
            size=40, translate=True),
            
        # Image:
        #'label_string_company_logo' 'label_string_partner_logo'
        #'label_string_linedrawing' 'label_string_product_image'
               
        # Counter:            
        'label_string_counter_pack': fields.char('Print counter pack', 
            size=40, translate=True),   

        # ---------------------------------------------------------------------
        #               SHOW HIDE ELEMENT IN REPORT DEPEND ON PARTNER:
        # ---------------------------------------------------------------------
        # Anagrafic text:
        'label_print_code': fields.boolean('Print company code'),
        'label_print_code_partner': fields.boolean('Print partner code'),
        'label_print_description': fields.boolean(
            'Print company description'),
        'label_print_description_partner': fields.boolean(
            'Print partner description'),
        'label_print_frame': fields.boolean('Print frame'),
        'label_print_fabric': fields.boolean('Print fabric'),

        # Anagrafic numeric:        
        'label_print_q_x_pack': fields.boolean('Print Q. x pack'),
        'label_print_q_x_pallet': fields.boolean('Print Q. x pallet'),
        'label_print_dimension': fields.boolean('Print dimension'),
        'label_print_volume': fields.boolean('Print volume'),
        'label_print_weight_net': fields.boolean('Print weight net'),
        'label_print_weight_lord': fields.boolean('Print weight lord'),
        'label_print_parcel': fields.boolean('Print parcel'),
        'label_print_price': fields.boolean('Print price'),
        'label_print_price_uom': fields.boolean('Print price uom'), # TODO add

        # EAN data:
        'label_print_ean13': fields.boolean('Print EAN13'),
        'label_print_ean8': fields.boolean('Print EAN8'),
        
        # Production:
        'label_print_line': fields.boolean('Print production line'),
        'label_print_period': fields.boolean('Print period',
            help='Production period YYMM  format es.: 1601'),
        'label_print_lot': fields.boolean('Print lot'),
        
        # Order:
        'label_print_order_ref': fields.boolean('Print order ref'), # customer
        'label_print_order_date': fields.boolean('Print order date'),
        'label_print_destination_code': fields.boolean(
            'Print destination code'),
            
        # Image:
        'label_print_company_logo': fields.boolean('Print company logo'),
        'label_print_partner_logo': fields.boolean('Print partner logo'),
        'label_print_linedrawing': fields.boolean('Print line drawing'),
        #'label_print_product_image': fields.boolean('Print product mage'), # TODO add what album
        
        # Extra images:
        'label_print_extra_image_ids': fields.many2many(
            'note.image', 'note_image_label_rel', 
            'label_id', 'image_id', 
            'Extra image'),
               
        # Counter:            
        'label_print_counter_pack': fields.boolean('Print counter pack',
            help='For print in label: 1/25, 2/25... (reset every product)'),   
        }
        
    _defaults = {
        # Show hide defaults:
        'label_print_code': lambda *x: True,
        'label_print_code_partner': lambda *x: True,
        'label_print_description': lambda *x: True,
        'label_print_description_partner': lambda *x: True,
        'label_print_frame': lambda *x: True,
        'label_print_fabric': lambda *x: True,
        'label_print_q_x_pack': lambda *x: True,
        
        'label_print_ean13': lambda *x: True,
        
        'label_print_line': lambda *x: True,
        'label_print_period': lambda *x: True,
        'label_print_lot': lambda *x: True,
        
        'label_print_company_logo': lambda *x: True,
        }
    
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
