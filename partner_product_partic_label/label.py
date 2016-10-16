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
        'force': fields.boolean(
            'Force', help='Force in label the use of own element'),
        'name': fields.selection([        
            ('ean13', 'EAN 13'),
            ('ean8', 'EAN 8'),            
            ('frame', 'Frame'),
            ('canvas', 'Canvas'),
            ('color', 'Color'),
            ('static_text1', 'Text 1'),
            ('static_text2', 'Text 2'),
            ('static_text3', 'Text 3'),
            ], 'name'),
        'partic_id': fields.many2one('res.partner.product.partic', 'Partic'),    
        }
    
class ResPartnerProductPartic(orm.Model):
    ''' Add product partic obj
    '''    
    _inherit = 'res.partner.product.partic'
    
    _columns = {
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

        # ---------------------------------------------------------------------
        #                              FORCE DATA:
        # ---------------------------------------------------------------------
        'label_use_ean': fields.boolean('Use customer EAN setted'),
        }

class ResPartner(orm.Model):
    ''' Add product partic obj
    '''    
    _inherit = 'res.partner'

    _columns = { 
        'label_ean': fields.selection([
            ('none', 'No barcode'),
            ('ean13', 'EAN 13'),
            ('ean8', 'EAN 8'),
            ], 'Use EAN', required=True),

        # ---------------------------------------------------------------------
        #                              FORCE DATA:
        # ---------------------------------------------------------------------
        'force_label_lang_id': fields.many2one(
            'res.lang', 'Label force lang', 
            help='Instead use partner lang (or label forced lang)'),

        # XXX now not used, maybe if general code parameter is adopted:
        #'label_force_customer_code': fields.boolean('Force customer code'),
        #'label_force_customer_name': fields.boolean('Force customer name'),
        
        # TODO logo management:
        'label_force_logo': fields.boolean('Force customer logo'),
        
        # ---------------------------------------------------------------------
        #                         USE DATA ELEMENT IN REPORT:
        # ---------------------------------------------------------------------
        'label_print_line': fields.boolean('Print production line'),
        'label_print_period': fields.boolean('Print line'),        
        'label_print_order_ref': fields.boolean('Print order ref'),
        'label_print_order_date': fields.boolean('Print order data'),
        'label_print_counter_pack': fields.boolean('Print counter pack'),        
        }
        
    _defaults = {
        lambda *x: 'label_ean': 'ean13',
        }    
    
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
