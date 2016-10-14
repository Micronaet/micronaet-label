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

# TODO manage printer for direct report with CUPS?
class LabelLabel(orm.Model):
    """ Model name: LabelLabel
    """

    _name = 'label.layout'
    _description = 'Label layout'

    _columns = {    
        'code': fields.char('Code', size=12), 
        'name': fields.char('Label format', size=64, required=True), 
        'note': fields.text('Note'),
        'continue': fields.boolean('Continue format'),
        
        # Dimension:
        'height': fields.float('Height', help='Height of label in mm.'),
        'width': fields.float('Width', help='Width of label in mm.'),
        
        # Interspace:
        'top': fields.float('Left', help='Top interspace in mm.'),
        'right': fields.float('Left', help='Right interspace in mm.'),
        'left': fields.float('Height', help='Left interspace in mm.'),        

        # Numer of label:
        'total': fields.integer('Total', help='Total label per row'),        
        }    

class LabelLabel(orm.Model):
    """ Model name: LabelLabel
    """

    _name = 'label.label'
    _description = 'Label'

    # -------------------------------------------------------------------------    
    #                            UTILITY:
    # -------------------------------------------------------------------------    
    # Parent management:
    def get_config_base_path(self, cr, uid, mode, context=None):
        ''' Read parameter: 
            mode = 'import' or 'datastore' path
        '''    
        if mode not in ['import', 'datastore']:
            raise osv.except_osv(
                _('Path error!'), 
                _('Path are only datastore or import not %s') % mode)
                
        key = 'label.label.%s.path' % mode
        
        config_pool = self.pool.get('ir.config_parameter')
        config_ids = config_pool.search(cr, uid, [
            ('key', '=', key)], context=context)
        if not config_ids:
            _logger.warning('Parameter not found: %s' % key)
            raise osv.except_osv(
                _('Parameter error'), 
                _('Setup init parameter: %s' % key),
                )

        config_proxy = config_pool.browse(
            cr, uid, config_ids, context=context)[0]
            
        # Create folder if not present:    
        os.system('mkdir -p %s' % config_proxy.value)     
        return config_proxy.value
    
    # -------------------------------------------------------------------------    
    #                              SCHEDULE EVENT:
    # -------------------------------------------------------------------------    
    # Import label (scheduled)
    def scheduled_import_label_label(self, cr, uid, context=None):
        ''' Import procedure for manage module
        '''
        extension = 'odt'
        
        report_pool = self.pool.get('ir.actions.report.xml')
        partner_pool = self.pool.get('res.partner')
        
        folder_in = os.path.expanduser(self.get_config_base_path(
            cr, uid, 'import', context=context))
        folder_out = os.path.expanduser(self.get_config_base_path(
            cr, uid, 'datastore', context=context))

        for f in os.listdir(folder_in):
            if f[-3:].lower() != extension: 
               continue # jump
               
            # -------------   
            # Create label:
            # -------------   
            name = f[:-4]
            
            # -----------------------------------------------------------------
            # Parse name for auto fill elements:
            # -----------------------------------------------------------------
            name_blocks = name.split('.')
            
            if len(name_blocks) == 4:
                # 0. partner
                partner_block = name_blocks[0] or False                
                partner_ids = partner_pool.search(cr, uid, [
                    ('label_code', '=', partner_block)], context=context)
                if partner_ids:
                    partner_id = partner_ids[0]
                else:
                    partner_ids = False    
            
                # 1. type:
                available_selection = [
                    item[0] for item in self._columns['type'].selection]
                if name_blocks[1] in available_selection:
                    type_block = name_blocks[1]
                    
                # 2. name:
                name_block = name_blocks[2] or name
                
                # 3. description:
                description_block = name_blocks[3] or name
                
                # 4. label format: # TODO
                
                # 5. language # TODO
                
            else:        
                # Defaulf value for 4 block:
                type_block = 'article'
                name_block = name
                description_block = name
                partner_id = False 

            label_id = self.create(cr, uid, {
                'type': type_block,
                'name': name_block,
                'description': description_block,
                'filename': f,
                'partner_id': partner_id,                
                }, context=context)
            
            # ----------------
            # File management:    
            # ----------------
            f_in = os.path.join(folder_in, f)   
            f_out = os.path.join(folder_out, '%s.%s' % (label_id, extension))
            try:
                os.rename(f_in, f_out)
            except:
                _logger.error('Error import label: %s/%s' % (folder_in, f))
                self.unlink(cr, uid, label_id, context=context)
                continue

            # --------------------
            # Create report aeroo:
            # --------------------
            report_id = report_pool.create(cr, uid, {
                'name': 'ID%s: %s' % (label_id, name_block),
                'type': 'ir.actions.report.xml',
                'model': 'label.label',
                'report_name': 'label_label_report_%s' % label_id,
                'report_type': 'aeroo',
                'in_format': 'oo-odt',
                #'out_format': 'oo-pdf',
                'parser_loc': 'label_system/report/label_parser.py',
                'report_rml': f_out,
                'parser_state': 'loc',
                'tml_source': 'file',
                }, context=context) 
                
            # ----------------------------
            # Update information on label:
            # ----------------------------
            self.write(cr, uid, label_id, {
                'report_id': report_id,
                }, context=context)                   
        return True

    # -------------------------------------------------------------------------    
    #                               BUTTON EVENT:
    # -------------------------------------------------------------------------        
    def test_report_label(self, cr, uid, ids, context=None):
        ''' Generate a test label
        '''
        assert len(ids) == 1, 'Works only with one record a time'
        
        label_proxy = self.browse(cr, uid, ids, context=context)[0]
        
        report_name = label_proxy.report_id.report_name
        return {
            'type': 'ir.actions.report.xml',
            'report_name': report_name,
            'datas': {
                'report_data': 'test',
                },
            }
        
    # -------------------------------------------------------------------------    
    #                               WORKFLOW EVENT:
    # -------------------------------------------------------------------------        
    def label_draft(self, cr, uid, ids, context=None):
        ''' Draft WF
        ''' 
        return self.write(cr, uid, ids, {
            'state': 'draft'}, context=context)
    
    def label_confirmed(self, cr, uid, ids, context=None):
        ''' Confirmed WF
        ''' 
        return self.write(cr, uid, ids, {
            'state': 'confirmed'}, context=context)

    def label_disabled(self, cr, uid, ids, context=None):
        ''' Disabled WF
        ''' 
        return self.write(cr, uid, ids, {
            'state': 'disabled'}, context=context)
        
    # -------------------------------------------------------------------------    
    #                                 ORM:
    # -------------------------------------------------------------------------        
    _columns = {
        'create_date': fields.date('Create date'),
        'code': fields.char('Code', size=12), 
        'name': fields.char('Label', size=64, required=True), 
        'description': fields.text('Description'),

        'filename': fields.char('Filename', size=64, 
            help='original file name'),
        'partner_id': fields.many2one(
            'res.partner', 'Partner'),
        'layout_id': fields.many2one(
            'label.layout', 'Layout format'),
        'report_id': fields.many2one(
            'ir.actions.report.xml', 'Report action'),
        
        'type': fields.selection([
            ('article', 'Article'),
            ('package', 'Package'),
            ('pallet', 'Pallet'),
            ('placeholder', 'Placeholder'),
            ], 'Type of label', required=True),
        
        'note': fields.text('Note'),
        
        # WF status:
        'state': fields.selection([
            ('draft', 'Draft'),
            ('confirmed', 'Confirmed'),
            ('disabled', 'Disabled'),
            ], 'State'),
        }
    
    _defaults = {
       'type': lambda *a: 'article',
       'state': lambda *x: 'draft',       
       }


class LabelLabel(orm.Model):
    """ Model name: Label saved for fast print
    """

    _name = 'label.label.fast'
    _description = 'Label fast'

    # -------------------------------------------------------------------------
    # Button event:
    # -------------------------------------------------------------------------
    def print_fast_label(self, cr, uid, ids, context=None):
        ''' Print this label
        '''
        fast_proxy = self.browse(cr, uid, ids, context=context)[0]
        
        report_name = fast_proxy.label_id.report_id.report_name
        return {
            'type': 'ir.actions.report.xml',
            'report_name': report_name,
            'datas': {
                'report_data': 'fast',
                'record_ids': ids,
                },
            }
        
    _columns = {
        'name': fields.char('Label name', size=64, required=True), 
        'label_id': fields.many2one('label.label', 'Label'),
        
        # -----------------------------------------------------------------
        # Label:
        # -----------------------------------------------------------------
        'counter': fields.integer('Counter', required=True, 
            help='Number of label printed'),
        'multi': fields.integer('Multilabel', help='Number of label per page'),
        #'lang',
                
        # -----------------------------------------------------------------
        # Product data:
        # -----------------------------------------------------------------
        'product_id': fields.many2one('product.product', 'Product'),
        'partner_id': fields.many2one('res.partner', 'Partner'),
        'order_id': fields.many2one('sale.order', 'Order'),
        'line_id': fields.many2one('sale.order.line', 'Order line'),
        'mrp_id': fields.many2one('mrp.production', 'Production'),
        
        # Description (force product if present):
        'force_name': fields.char('Force name', size=64), 
        'force_customer_name': fields.char('Force name', size=64),
        'force_frame': fields.text('Force frame'), 
        'force_color': fields.text('Force color'), 
        'force_canvas': fields.text('Force canvas'), 

        # Code:
        'force_code': fields.char('Force code', size=20), 
        'force_customer_code': fields.char('Force customer code', size=20), 
        'force_codebar': fields.char('Force codebar', size=13), 
        
        # Extra:            
        'force_q_x_pack': fields.integer('Force q. x pack'),
        
        # Static:
        'static_text1': fields.text('Static text 1'), 
        'static_text2': fields.text('Static text 2'), 
        'static_text3': fields.text('Static text 3'), 
        
        # -----------------------------------------------------------------
        # Production:
        # -----------------------------------------------------------------
        # Line:
        'line': fields.char('Line', size=20, help='Production line'), 
        'period': fields.char('Period', size=20, 
            help='Production period YYMM  format es.: 1601'), 
        
        # Order:
        'order_ref': fields.char('Order ref', size=30), 
        'order_date': fields.date('Order date'), 

        # Counter:
        'counter_pack_total': fields.integer('Counter pack total',
            help='Total pack for format: 1 / 25 (reset every product)'),
        
        # -----------------------------------------------------------------
        # Logo:
        # -----------------------------------------------------------------
        # TODO
        # Logo Image:
        'with_company_logo': fields.boolean('With company logo'),
        'with_customer_logo': fields.boolean('With customer logo'),
        'with_recycle_logo': fields.boolean('With recycle logo'),
        # Picture image:
        'with_image_logo': fields.boolean('With image logo'),
        'with_drawing_logo': fields.boolean('With drawing logo'),
        }
        
    _defaults = {
        'counter': lambda *x: 1,
        }
        
class LabelLabel(orm.Model):
    """ Model name: Label relations
    """

    _inherit = 'label.label'
    
    _columns = {
        'fast_ids': fields.one2many(
            'label.label.fast', 'label_id', 'Fast label'),
        }

class ResPartnerLabel(orm.Model):
    """ Model name: Partner extra fields
    """

    _inherit = 'res.partner'
    
    _columns = {
        'label_code': fields.char('Label code', size=30, 
            help='Partner label code, used for auto import partner'),
        }
       
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
