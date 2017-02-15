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
    
    def assign_single_ean_13(self, cr, uid, ids, context=None):
        ''' Copy single code in ean13
        '''
        current_proxy = self.browse(cr, uid, ids, context=context)[0]
        return self.write(cr, uid, ids, {
            'ean13': current_proxy.ean13_s,
            }, context=context)

    def assign_pack_ean_13(self, cr, uid, ids, context=None):
        ''' Copy pack code in ean13
        '''
        current_proxy = self.browse(cr, uid, ids, context=context)[0]
        return self.write(cr, uid, ids, {
            'ean13': current_proxy.ean13_p,
            }, context=context)

    def assign_org_ean_13(self, cr, uid, ids, context=None):
        ''' Copy org code in ean13
        '''
        current_proxy = self.browse(cr, uid, ids, context=context)[0]
        return self.write(cr, uid, ids, {
            'ean13': current_proxy.ean13_org,
            }, context=context)

    def import_barcode(self, cr, uid, ids, context=None):
        ''' Import barcode
        '''
        ''' Read XLS file for reassociate inventory category
        ''' 
        product_pool = self.pool.get('product.product')

        filename = '/home/administrator/photo/xls/barcode.xls'

        try:
            WB = xlrd.open_workbook(filename)
        except:
            raise osv.except_osv(
                _('Error XLSX'), 
                _('Cannot read XLS file: %s' % filename),
                )
        import pdb; pdb.set_trace()       
        WS = xl_workbook.sheet_by_index(0)
        for row in range(0, WS.nrows):
            # Read data from file:
            default_code = WS.cell(row_idx, 0)
            ean13 = WS.cell(row_idx, 2)
            ean13_s = WS.cell(row_idx, 4)
            ean13_p = WS.cell(row_idx, 5)
            
            product_ids = self.search(cr, uid, [
                ('default_code', '=', default_code),
                ], context=context)
                
            if not product_ids:
                _logger.error('Code not found: %s' % default_code)
                continue
                
            if len(product_ids) > 1:
                _logger.warning('Code double: %s' % default_code)
                    
                         
            product_proxy = self.browse(
                cr, uid, product_ids, context=context)[0]
            
            ean13_current = product_proxy.ean13
            ean13_org = product_proxy.ean13_org
            
            data = {
                ('ean13', '=', ean13),
                ('ean13_s', '=', ean13_s),
                ('ean13_p', '=', ean13_p),
                }
            if not ean_org and ean13 != ean13_current:
                data['ean13_org'] = ean13_current
                
            product_pool.write(cr, uid, product_ids, data, context=context)        
        return True
        
        
    _columns = {
        'ean13_s': fields.char('EAN 13 Single product', size=13),
        'ean13_p': fields.char('EAN 13 Pack product', size=13),     
        'ean13_org': fields.char('EAN 13 Org', size=13),     
        }
    
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
