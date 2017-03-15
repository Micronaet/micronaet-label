#!/usr/bin/python
# -*- coding: utf-8 -*-
##############################################################################
#
#   Copyright (C) 2010-2012 Associazione OpenERP Italia
#   (<http://www.openerp-italia.org>).
#   Copyright(c)2008-2010 SIA "KN dati".(http://kndati.lv) All Rights Reserved.
#                   General contacts <info@kndati.lv>
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU Affero General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU Affero General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
import os
import sys
import logging
from openerp.report import report_sxw
from openerp.report.report_sxw import rml_parse
from datetime import datetime, timedelta
from openerp.tools.translate import _
from openerp.tools import (DEFAULT_SERVER_DATE_FORMAT, 
    DEFAULT_SERVER_DATETIME_FORMAT, 
    DATETIME_FORMATS_MAP, 
    float_compare)

_logger = logging.getLogger(__name__)


class Parser(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(Parser, self).__init__(cr, uid, name, context)
        self.localcontext.update({            
            'get_report_single_label': self.get_report_single_label,
            })
            
    def get_report_single_label(self, o):
        ''' Prepare report pallet for element
        '''
        import pdb; pdb.set_trace()
        res = {}
        for line in sorted(o.order_line_ids, key=lambda x: x.sequence):
            # -----------------------------------------------------------------
            # Has pallet label:
            # -----------------------------------------------------------------
            if not line.partner_id.has_pallet_label:
                continue
            product = line.product_id
            
            # -----------------------------------------------------------------
            # Get q per pallet:
            # -----------------------------------------------------------------
            # Data used in quotation:
            try:
                item_per_pallet = int(product.item_per_pallet)
            except:
                item_per_pallet = 0
            # Data used for label:
            q_x_pallet = product.q_x_pallet or item_per_pallet
            
            # -----------------------------------------------------------------
            # Partner address 
            # -----------------------------------------------------------------
            key = item.partner_id, item.address_id, item.product_id

            if key not in res:
                res[key] = [q_x_pallet, item.product_qty]
        pallet = []
        for key in res:
            q_x_pallet, total = res[key]
            loop = total \ q_x_pallet
            if total % q_x_pallet != 0:
                loop += 1
            remain = total
            for i in range(0, loop):
                remain -= q_x_pallet
                pallet.append((
                    key, 
                    remain if remain < p_x_pallet else q_x_pallet,
                    ))
        return pallet   
                
        
            
        return 
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
