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

    _columns = { 
        # ---------------------------------------------------------------------
        #                      EXTRA LANGUAGE ELEMENTS:
        # ---------------------------------------------------------------------
        'label_lang_code': fields.char(
            'Print company code', 
            size=40, help='Extra lang code, use format: EN|DE|FR|IT'),
        'label_lang_description': fields.char(
            'Print company description', 
            size=40, help='Extra lang code, use format: EN|DE|FR|IT'),
        'label_lang_frame': fields.char('Print frame',
            size=40, help='Extra lang code, use format: EN|DE|FR|IT'),
        'label_lang_fabric': fields.char('Print fabric', 
            size=40, help='Extra lang code, use format: EN|DE|FR|IT'), 

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
        'label_print_frame': fields.boolean('Print frame'), # TODO add
        'label_print_fabric': fields.boolean('Print fabric'), # TODO add

        # Anagrafic numeric:        
        'label_print_q_x_pack': fields.boolean('Print Q. x pack'),
        'label_print_q_x_pallet': fields.boolean('Print Q. x pallet'),#TODO add
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
        'label_print_period': fields.boolean('Print period'),
        'label_print_lot': fields.boolean('Print lot'),
        
        # Order:
        'label_print_order_ref': fields.boolean('Print order ref'), # customer
        'label_print_order_date': fields.boolean('Print order date'),
        'label_print_destination_code': fields.boolean(
            'Print destination code'),
            
        # Image:
        'label_print_company_logo': fields.boolean('Print company logo'),
        'label_print_partner_logo': fields.boolean('Print partner logo'), # TODO add
        'label_print_linedrawing': fields.boolean('Print line drawing'), # TODO add
        #'label_print_product_image': fields.boolean('Print product mage'), # TODO add what album
        
        # Extra images:
        'label_print_extra_image_ids': fields.many2many(
            'note.image', 'note_image_label_rel', 
            'label_id', 'image_id', 
            'Extra image'),
               
        # Counter:            
        'label_print_counter_pack': fields.boolean('Print counter pack'),   
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
