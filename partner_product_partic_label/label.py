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
    
    def get_tri_state(self, cr, uid, context=None):
        return [ 
            ('show', 'Show'), # ON
            ('hide', 'Hide'), # OFF 
            #('not', 'Not selected'), # NOT PRESENT
            ]
    
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
        # UTILITY FUNCTION:
        # ---------------------------------------------------------------------
        def get_label(company, partner, address, field):
            ''' Check field from address, partner, company return first found
            '''
            if address:
                res = address.__getattribute__(field) or \
                    partner.__getattribute__(field) or \
                    company.partner_id.__getattribute__(field) or ''
            else:    
                res = partner.__getattribute__(field) or\
                    company.partner_id.__getattribute__(field) or ''            
            if not res:
                # TODO raise error?
                _logger.warning('Field %s not found string value!' % field)            
            return res

        def get_state_value(company, partner, address, field, warning=False):
            ''' Check field from address, partner, company return state value
                as True or False
            '''
            if address:
                res = address.__getattribute__(field) or \
                    partner.__getattribute__(field) or \
                    company.partner_id.__getattribute__(field) or ''
            else:    
                res = partner.__getattribute__(field) or\
                    company.partner_id.__getattribute__(field) or ''            
            if warning and not res:
                _logger.warning('Field %s not set up as show or hide!' % field) 

            if res == 'show':
                return True
            else:
                return False
        
        # ---------------------------------------------------------------------
        # Read parameters:
        # ---------------------------------------------------------------------
        context = parameter.get('context', {})
        line = parameter.get('line', False)
        
        # Pool used:
        product_pool = self.pool.get('product.product')
        partner_pool = self.pool.get('res.partner') # and also address
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
            record = {
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
            
            # Check mandatory ID (else no data for label)
            if product_id:
                product = product_pool.browse(
                    cr, uid, product_id, context=context)
            else: # Mandatory element, raise error
                raise osv.except_osv(
                    _('No data'), 
                    _('Product ref. not present'),
                    )                
            if partner_id:
                partner = partner_pool.browse(
                    cr, uid, partner_id, context=context)
            else: # Mandatory element, raise error
                raise osv.except_osv(
                    _('No data'), 
                    _('Partner ref. not present'),
                    )
            if address_id:
                address = partner_pool.browse(
                    cr, uid, address_id, context=context)
            else:
                address = False # not mandatory
            if order_id:
                order = order_pool.browse(
                    cr, uid, order_id, context=context)
            else: # Mandatory element, raise error
                raise osv.except_osv(
                    _('No data'), 
                    _('Order ref. not present'),
                    )
            if mrp_id:
                mrp = mrp_pool.browse(
                    cr, uid, mrp_id, context=context)
            else: # Mandatory element, raise error
                raise osv.except_osv(
                    _('No data'), 
                    _('MRP ref. not present'),
                    )

            # Create record of m2o                
            record = {
                'product_id': product_id,
                'partner_id': partner_id,
                'address_id': address_id,
                'order_id': order_id,
                'line_id': False,
                'mrp_id': mrp_id,
                }

        company = partner.company_id # Common reference
                
        # ---------------------------------------------------------------------
        # Check parameter in partner address form:
        # ---------------------------------------------------------------------
        # Check and label string from address or partner setup:
        record.update({
            # -----------------------------------------------------------------
            # String label:
            # -----------------------------------------------------------------
            # Anagrafic text:
            'record_string_code': get_label(
                company, partner, address, 
                'label_string_code'),
            'record_string_code_partner': get_label(
                company, partner, address, 
                'label_string_code_partner'),
            'record_string_description': get_label(
                company, partner, address, 
                'label_string_description'),
            'record_string_description_partner': get_label(
                company, partner, address, 
                'label_string_description_partner'),
            'record_string_frame': get_label(
                company, partner, address, 
                'label_string_frame'),
            'record_string_fabric': get_label(
                company, partner, address, 
                'label_string_fabric'),

            # Anagrafic numeric:
            'record_string_q_x_pack': get_label(
                company, partner, address, 
                'label_string_q_x_pack'),
            'record_string_q_x_pallet': get_label(
                company, partner, address, 
                'label_string_q_x_pallet'),
            'record_string_dimension': get_label(
                company, partner, address, 
                'label_string_dimension'),
            'record_string_volume': get_label(
                company, partner, address, 
                'label_string_volume'),
            'record_string_weight_net': get_label(
                company, partner, address, 
                'label_string_weight_net'),
            'record_string_weight_lord': get_label(
                company, partner, address, 
                'label_string_weight_lord'),
            'record_string_parcel': get_label(
                company, partner, address, 
                'label_string_parcel'),
            'record_string_price': get_label(
                company, partner, address, 
                'label_string_price'),
            
            # EAN (no label):
            
            # Production:
            'record_string_line': get_label(
                company, partner, address, 
                'label_string_line'),
            'record_string_period': get_label(
                company, partner, address, 
                'label_string_period'), 
            'record_string_lot': get_label(
                company, partner, address, 
                'label_string_lot'),
                
            # Order:
            'record_string_order_ref': get_label(
                company, partner, address, 
                'label_string_order_ref'), 
            'record_string_order_date': get_label(
                company, partner, address, 
                'label_string_order_date'), 
            'record_string_destination_code': get_label(
                company, partner, address, 
                'label_string_destination_code'), 
            
            # Image (no label):
            
            # Counter:
            'record_string_counter_pack': get_label(
                company, partner, address, 
                'label_string_counter_pack'),  

            # -----------------------------------------------------------------
            # Hide Show check for label (form partner tri-state):
            # -----------------------------------------------------------------
            # Anagrafic text:
            'record_print_code': get_state_value(
                company, partner, address, 
                'label_print_code'),
            'record_print_code_partner': get_state_value(
                company, partner, address, 
                'label_print_code_partner'),
            'record_print_description': get_state_value(
                company, partner, address, 
                'label_print_description'), 
            'record_print_description_partner': get_state_value(
                company, partner, address, 
                'label_print_description_partner'), 
            'record_print_frame': get_state_value(
                company, partner, address, 
                'label_print_frame'),
            'record_print_fabric': get_state_value(
                company, partner, address, 
                'label_print_fabric'),

            # Anagrafic numeric:
            'record_print_q_x_pack': get_state_value(
                company, partner, address, 
                'label_print_q_x_pack'), 
            'record_print_q_x_pallet': get_state_value(
                company, partner, address, 
                'label_print_q_x_pallet'), 
            'record_print_dimension': get_state_value(
                company, partner, address, 
                'label_print_dimension'), 
            'record_print_volume': get_state_value(
                company, partner, address, 
                'label_print_volume'), 
            'record_print_weight_net': get_state_value(
                company, partner, address, 
                'label_print_weight_net'), 
            'record_print_weight_lord': get_state_value(
                company, partner, address, 
                'label_print_weight_lord'),
            'record_print_parcel': get_state_value(
                company, partner, address, 
                'label_print_parcel'), 
            'record_print_price': get_state_value(
                company, partner, address, 
                'label_print_price'), 
            'record_print_price_uom': get_state_value(
                company, partner, address, 
                'label_print_price_uom'),

            # EAN data:
            'record_print_ean13': get_state_value(
                company, partner, address, 
                'label_print_ean13'), 
            'record_print_ean8': get_state_value(
                company, partner, address, 
                'label_print_ean8'), 
            
            # Production:
            'record_print_line': get_state_value(
                company, partner, address, 
                'label_print_line'),
            'record_print_period': get_state_value(
                company, partner, address, 
                'label_print_period'),
            'record_print_lot': get_state_value(
                company, partner, address, 
                'label_print_lot'), 
            
            # Order:
            'record_print_order_ref': get_state_value(
                company, partner, address, 
                'label_print_order_ref'),
            'record_print_order_date': get_state_value(
                company, partner, address, 
                'label_print_order_date'),
            'record_print_destination_code': get_state_value(
                company, partner, address, 
                'label_print_destination_code'),
                
            # Image:
            'record_print_company_logo': get_state_value(
                company, partner, address, 
                'label_print_company_logo'), 
            'record_print_partner_logo': get_state_value(
                company, partner, address, 
                'label_print_partner_logo'), 
            'record_print_linedrawing': get_state_value(
                company, partner, address, 
                'label_print_linedrawing'), 
            #'label_print_product_image': 
            
            # Counter:            
            'record_print_counter_pack': get_state_value(
                company, partner, address, 
                'label_print_counter_pack'),  

            # TODO remove:
            #'record_counter_pack_total':            
            })
               
        
        # ---------------------------------------------------------------------
        # Product, MRP, Order data fields:
        # ---------------------------------------------------------------------
        # Get complex field:
        try:
            line = mrp.lavoration_ids[0].workcenter_id.code
        except:
            _logger.error('No line!')
            line = ''
        
        # Update record with data:    
        record.update({
            # -----------------------------------------------------------------
            #                               PRODUCT:
            # -----------------------------------------------------------------
            'record_data_code': product.default_code,
            'record_data_code_partner': 'TODO', # TODO
            'record_data_description': product.name, # TODO use label name?
            'record_data_description_partner': 'TODO', # TODO 
            'record_data_frame': 'TODO', # TODO
            'record_data_fabric': 'TODO', # TODO

            # Anagrafic numeric:        
            # TODO change float
            'record_data_q_x_pack': product.q_x_pack or '',
            'record_data_q_x_pallet': product.q_x_pallet or '',
            'record_data_dimension': '%sx%sx%s' % (
                product.height, product.width, product.length) if (
                    product.height and product.width and product.lenght) else\
                        '',
            'record_data_volume': product.volume,
            'record_data_weight_net': product.weight_net,
            'record_data_weight_lord': product.weight,
            'record_data_parcel': 'TODO' or product.parcel,
            'record_data_price': product.lst_price, # TODO
            'record_data_price_uom': product.uom_id.name,

            # EAN data:
            'record_data_ean13': product.ean13, # TODO 
            'record_data_ean8': product.ean8, # TODO
            
            # -----------------------------------------------------------------
            #                                MRP:
            # -----------------------------------------------------------------
            'record_data_line': line,
            'record_data_period': '%s%s' % (
                mrp.date_planned[2:4], mrp.date_planned[5:7]),
            'record_data_lot': mrp.name.replace('MO', '').lstrip('0'),
            
            # -----------------------------------------------------------------
            #                               ORDER:
            # -----------------------------------------------------------------
            'record_data_order_ref': order.client_order_ref or '', #label_order
            'record_data_order_date': order.date_order[:10],
            'record_data_destination_code': order.destination_partner_id.ref\
                if order.destination_partner_id else '',
                
            # -----------------------------------------------------------------
            #                               IMAGES:
            # -----------------------------------------------------------------
            # Image:
            # XXX Note: used related elements
            #record_data_company_logo 
            #'record_data_partner_logo': order.company_id.partner_id.label_logo,
            #record_data_linedrawing label_print_product_image        
            
            # Extra images:
            # XXX Note: used related elements
            #record_data_extra_image_ids
            
            # -----------------------------------------------------------------
            #                            STATIC TEXT:
            # -----------------------------------------------------------------
            'record_data_text1': 'TODO', # TODO
            'record_data_text2': 'TODO', # TODO
            'record_data_text3': 'TODO', # TODO
            })
            
        return record        

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
        # XXX Note: element are in 3-state for parent required selection!
        
        # Anagrafic text:
        'label_print_code': fields.selection(get_tri_state, 
            'Print company code'),
        'label_print_code_partner': fields.selection(get_tri_state, 
            'Print partner code'),
        'label_print_description': fields.selection(get_tri_state, 
            'Print company description'),
        'label_print_description_partner': fields.selection(get_tri_state, 
            'Print partner description'),
        'label_print_frame': fields.selection(get_tri_state, 
            'Print frame'),
        'label_print_fabric': fields.selection(get_tri_state, 
            'Print fabric'),

        # Anagrafic numeric:        
        'label_print_q_x_pack': fields.selection(get_tri_state, 
            'Print Q. x pack'),
        'label_print_q_x_pallet': fields.selection(get_tri_state, 
            'Print Q. x pallet'),
        'label_print_dimension': fields.selection(get_tri_state, 
            'Print dimension'),
        'label_print_volume': fields.selection(get_tri_state, 
            'Print volume'),
        'label_print_weight_net': fields.selection(get_tri_state, 
            'Print weight net'),
        'label_print_weight_lord': fields.selection(get_tri_state, 
            'Print weight lord'),
        'label_print_parcel': fields.selection(get_tri_state, 
            'Print parcel'),
        'label_print_price': fields.selection(get_tri_state, 
            'Print price'),
        'label_print_price_uom': fields.selection(get_tri_state, 
            'Print price uom'), # TODO add

        # EAN data:
        'label_print_ean13': fields.selection(get_tri_state, 
            'Print EAN13'),
        'label_print_ean8': fields.selection(get_tri_state, 
            'Print EAN8'),
        
        # Production:
        'label_print_line': fields.selection(get_tri_state, 
            'Print production line'),
        'label_print_period': fields.selection(get_tri_state, 
            'Print period',
            help='Production period YYMM  format es.: 1601'),
        'label_print_lot': fields.selection(get_tri_state, 
            'Print lot'),
        
        # Order:
        'label_print_order_ref': fields.selection(get_tri_state, 
            'Print order ref'), # customer
        'label_print_order_date': fields.selection(get_tri_state, 
            'Print order date'),
        'label_print_destination_code': fields.selection(get_tri_state, 
            
            'Print destination code'),
            
        # Image:
        'label_print_company_logo': fields.selection(get_tri_state, 
            'Print company logo'),
        'label_print_partner_logo': fields.selection(get_tri_state, 
            'Print partner logo'),
        'label_print_linedrawing': fields.selection(get_tri_state, 
            'Print line drawing'),
        #'label_print_product_image': fields.selection(get_tri_state, 
        #    'Print product mage'), # TODO add what album
        
        # Extra images:
        'label_print_extra_image_ids': fields.many2many(
            'note.image', 'note_image_label_rel', 
            'label_id', 'image_id', 
            'Extra image'),
               
        # Counter:            
        'label_print_counter_pack': fields.selection(get_tri_state, 
            'Print counter pack',
            help='For print in label: 1/25, 2/25... (reset every product)'),   
        }
        
    _defaults = {
        # Show hide defaults:
        # XXX Set up in company partner!!
        #'label_print_code': lambda *x: 'show',
        #'label_print_code_partner': lambda *x: 'show',
        #'label_print_description': lambda *x: 'show',
        #'label_print_description_partner': lambda *x: 'show',
        #'label_print_frame': lambda *x: 'show',
        #'label_print_fabric': lambda *x: 'show',
        #'label_print_q_x_pack': lambda *x: 'show',
        
        #'label_print_ean13': lambda *x: 'show',
        
        #'label_print_line': lambda *x: 'show',
        #'label_print_period': lambda *x: 'show',
        #'label_print_lot': lambda *x: 'show',
        
        #'label_print_company_logo': lambda *x: 'show',
        }
    
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
