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


class SaleOrder(orm.Model):
    """ Model name: SaleOrder
    """
    _inherit = 'sale.order'

    _columns = {
        'client_order_code': fields.char(
            'Codice ordine', size=64, help='Order code used in label'
            ),
        }


class MrpProduction(orm.Model):
    """ Force product only in production
    """
    _inherit = 'mrp.production'

    # -------------------------------------------------------------------------
    # Utility:
    # -------------------------------------------------------------------------
    def force_product_extra_label_field(self, cr, uid, ids, context=None):
        """ Update extra fields product
        """
        if context is None:
            context = {}

        # Pool used:
        product_pool = self.pool.get('product.product')

        product_ids = []
        for line in self.browse(cr, uid, ids, context=context)[
                0].order_line_ids:
            product_id = line.product_id.id
            if line.product_id.structure_id and line.product_id.default_code:
                if product_id not in product_ids:
                    product_ids.append(product_id)
            else:
                _logger.error(
                    'Product no structure/code %s' % line.product_id.name)

        ctx = context.copy()
        ctx['update_only_field'] = ('label_frame', 'label_fabric_color')
        ctx['log_file'] = '/home/administrator/photo/Label/log/speech.csv'

        for product in product_pool.browse(
                cr, uid, product_ids, context=context):
            product_pool.generate_name_from_code(
                cr, uid, [product.id], context=ctx)
            _logger.info('Update label field: %s' % product.default_code)
        return True


class ProductProduct(orm.Model):
    """ Model name: Add extra fields to product
    """
    _inherit = 'product.product'

    # -------------------------------------------------------------------------
    # Override:
    # -------------------------------------------------------------------------
    def get_all_fields_to_update(self, all_db=None):
        """ Override function for update other fields:
        """
        res = {}

        if all_db is None:
            _logger.warning('No all_db for generate extra fields')
            return res

        #_logger.warning('All DB database: %s' % (all_db, ))
        if 'C' in all_db:
            res['label_frame'] = all_db['C']
        else:
            _logger.error('Cannot set frame field')
            res['label_frame'] = ''

        if 'D' in all_db:
            res['label_fabric_color'] = all_db['D']
        else:
            res['label_fabric_color'] = ''
            _logger.error('Cannot set color field')
        return res

    _columns = {
        'label_frame': fields.char('Label Frame', size=64, translate=True),
        'label_fabric_color': fields.char('Label fabric color', size=64,
            translate=True),
        'ean8': fields.char('EAN 8', size=8),
        'q_x_pallet': fields.integer('Q. per pallet'),
        }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
