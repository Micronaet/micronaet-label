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

class ProductProduct(orm.Model):
    """ Model name: ProductProduct
    """    
    _inherit = 'product.product'
    
    def _function_get_ean_single_product(
            self, cr, uid, ids, fields, args, context=None):
        ''' Fields function for calculate single EAN for 8 and 13 elements
            single depend on q_x_pack field and for 
            char S in 13rd position
        '''
        _logger.warning('>> Searcing EAN for single product...')
        if context is None:
            context = {}
        
        if context.get('no_ean_mono_value', False):
            return dict.fromkeys(ids, False)
            
        res = {}

        for product in self.browse(cr, uid, ids, context=context):
            # -----------------------------------------------------------------
            # Q x pack is yet single:
            # -----------------------------------------------------------------
            if product.q_x_pack == 1:
                res[product.id] = {
                    'ean13_mono': product.ean13,
                    'ean8_mono': product.ean8,                                      
                    }
            # -----------------------------------------------------------------
            # Q x pack is package:
            # -----------------------------------------------------------------
            else: # search code with S in 13
                default_code = product.default_code                    
                
                # -------------------------------------------------------------
                # Code not has single: 
                # -------------------------------------------------------------
                if not default_code or len(default_code) > 12:
                    res[product.id] = {
                        'ean13_mono': False,
                        'ean8_mono': False,
                        }
                    _logger.warning('No single EAN code >= 13 char')

                # -------------------------------------------------------------
                # Code has single: 
                # -------------------------------------------------------------
                else:
                    product_ids = self.search(cr, uid, [
                        ('default_code', '=', '%-12sS' % default_code),
                        ], context=context)
                    if product_ids: # XXX more than one?
                        if len(product_ids) > 1:
                            _logger.warning(
                                'More single EAN code %s' % default_code)
                        single_proxy = self.browse(
                            cr, uid, product_ids, context=context)[0]
                        res[product.id] = {
                            'ean13_mono': single_proxy.ean13,
                            'ean8_mono': single_proxy.ean8,
                            }
                    else:
                        _logger.warning(
                            'Single product not found %s' % default_code)
                        res[product.id] = {
                            'ean13_mono': False,
                            'ean8_mono': False,
                            }
        return res
        
    _columns = {
        'ean13_mono': fields.function(
            _function_get_ean_single_product, method=True, type='char', 
            string='EAN 13 single', store=False, multi=True), 
        'ean8_mono': fields.function(
            _function_get_ean_single_product, method=True, type='char', 
            string='EAN 8 single', store=False, multi=True),                        
        }
    
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
