##############################################################################
#
# Copyright (c) 2008-2010 SIA "KN dati". (http://kndati.lv) All Rights Reserved.
#                    General contacts <info@kndati.lv>
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsability of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# garantees and support are strongly adviced to contract a Free Software
# Service Company
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
##############################################################################

from openerp.report import report_sxw
from openerp.report.report_sxw import rml_parse

class Parser(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(Parser, self).__init__(cr, uid, name, context)
        self.localcontext.update({
            'get_partner_ean': self.get_partner_ean,           
            })
    
    def get_partner_ean(self, o):
        ''' Search document for this partner and collect product ean
        '''
        cr = self.cr
        uid = self.uid
        context = {}
        
        # Pool used:
        order_pool = self.pool.get('sale.order.line')
        pick_pool = self.pool.get('stock.move')
        product_pool = self.pool.get('product.product')

        # Get product from order:
        line_ids = order_pool.search(cr, uid, [
            ('order_id.partner_id', '=', o.id),
            ], context=context)
        product_ids = [item.product_id.id for item in order_pool.browse(
            cr, uid, line_ids, context=context)]
        
        # Get product from picking:
        move_ids = pick_pool.search(cr, uid, [
            ('picking_id.partner_id', '=', o.id),
            ], context=context)
        product_ids.extend([item.product_id.id for item in pick_pool.browse(
            cr, uid, move_ids, context=context)])
        product_ids = tuple(set(product_ids))
        
        res = product_pool.browse(cr, uid, product_ids, context=context)
        return sorted(res, key=lambda x: (x.default_code, x.name))
