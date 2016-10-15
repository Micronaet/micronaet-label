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

label_type = [
    ('article', 'Article'),
    ('package', 'Package'),
    ('pallet', 'Pallet'),
    ('placeholder', 'Placeholder'),
    ]
    
# TODO manage printer for direct report with CUPS?
class LabelLabel(orm.Model):
    """ Model name: Label master object
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
                
                # 6. code # TODO
                
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
            _logger.info('Label imported: %s' % f)    
        return True

    # -------------------------------------------------------------------------    
    #                               BUTTON EVENT:
    # -------------------------------------------------------------------------        
    def test_report_label(self, cr, uid, ids, context=None):
        ''' Generate a test label
        '''
        assert len(ids) == 1, 'Works only with one record a time'
        
        job_pool = self.pool.get('label.label.job')
        job_ids = job_pool.seach(cr, uid, [
            ('demo', '=', True)], context=context)
        if not job_ids:
            raise osv.except_osv(
                _('Error print'), 
                _('No DEMO label on label jobs'),
                )
        if len(job_ids) > 1:
            _logger.error('More DEMO label!!')        
            
        label_proxy = self.browse(cr, uid, ids, context=context)[0]
        
        report_name = label_proxy.report_id.report_name
        return {
            'type': 'ir.actions.report.xml',
            'report_name': report_name,
            'datas': {
                'record_ids': job_ids,
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
        
        'type': fields.selection(label_type, 'Type of label', required=True),
        'lang_id': fields.many2one('res.lang', 'Lang', 
            help='For fixed text, data element will be loaded as setup'),
        
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


class LabelLabelReportJob(orm.Model):
    """ Model name: Label report job
    """
    _name = 'label.label.report'
    _description = 'Label Report Job'
    
    # Schedule action:
    def clean_report_function(self, cr, uid, days=10, contextc=None):
        ''' Clean report more older than 10 days (but only line not fast)
        ''' 
        return True
    
    # Button event:
    def print_report_job(self, cr, uid, ids, context=None):
        ''' Print all label in order        
        '''
        assert len(ids) == 1, 'Works only with one record a time'
        
        report_proxy = self.browse(cr, uid, ids, context=context)[0]
        
        res = [] # TODO generate PDF and aggregate!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
        for job in report_proxy.job_ids:
            report_name = job_proxy.label_id.report_id.report_name
            res = {
                'type': 'ir.actions.report.xml',
                'report_name': report_name,
                'datas': {
                    'record_ids': [job.id],
                    },
                }
        return True
        
    _columns = {
        'name': fields.char('Name', size=64, required=True),
        'create_date': fields.date('Create date'),
        'create_uid': fields.many2one(
            'res.users', 'Create user'),
        }

class LabelLabelJob(orm.Model):
    """ Model name: Label saved for job print
        NOTE: all field load in record element start with "record_"
    """

    _name = 'label.label.job'
    _description = 'Label job'
    _order = 'report_id,sequence'
    
    # -------------------------------------------------------------------------
    # Button event:
    # -------------------------------------------------------------------------
    def set_fast_label_on(self, cr, uid, ids, context=None):
        ''' Set fast label on
        '''
        return self.write(cr, uid, ids, {
            'fast': True,
            }, context=context)
            
    def set_fast_label_off(self, cr, uid, ids, context=None):
        ''' Set fast label off
        '''
        return self.write(cr, uid, ids, {
            'fast': False,
            }, context=context)
            
    def generate_text_data_from_linked(self, cr, uid, ids, context=None):
        ''' Generate text data from linked object present
        '''
        return True
        
    def print_fast_label(self, cr, uid, ids, context=None):
        ''' Print this label
        '''
        job_proxy = self.browse(cr, uid, ids, context=context)[0]
        
        report_name = job_proxy.label_id.report_id.report_name
        return {
            'type': 'ir.actions.report.xml',
            'report_name': report_name,
            'datas': {
                'record_ids': ids,
                },
            }
        
    _columns = {
        # Label definition:
        'sequence': fields.integer('Sequence'),
        'label_id': fields.many2one('label.label', 'Label'),
        'report_id': fields.many2one('label.label.report', 'Report job'),
        'lang_id': fields.many2one('res.lang', 'Lang'),
        'demo': fields.boolean('Demo'), 
        'fast': fields.boolean('Fast label', 
            help='Job that is never cleaned, used sometimes for print direct'),

        # Layout reference:
        'layout_id': fields.related(
            'label_id', 'layout_id', 
            type='many2one', relation='label.layout', 
            string='Layout', readonly=True),
        'type': fields.related(
            'label_id', 'type', selection=label_type,
            type='selection', string='Type', readonly=True),

                
        # -----------------------------------------------------------------
        #                          Linked object:
        # -----------------------------------------------------------------
        'product_id': fields.many2one('product.product', 'Product'),
        'partner_id': fields.many2one('res.partner', 'Partner', 
            domain=[('is_company', '=', True), ('is_address', '=', False)]),
        'address_id': fields.many2one('res.partner', 'Address', 
            domain=[('is_address', '=', True)]),
        'order_id': fields.many2one('sale.order', 'Order'),
        'line_id': fields.many2one('sale.order.line', 'Order line'),
        'mrp_id': fields.many2one('mrp.production', 'Production'),

        # -----------------------------------------------------------------
        #                               RECORD:
        # -----------------------------------------------------------------        
        'record_counter': fields.integer('Counter', required=True, 
            help='Number of label printed'),
        
        # -----------------------------------------------------------------
        #                          Product data:
        # -----------------------------------------------------------------
        # Description (force product if present):
        'record_name': fields.char('Product name', size=64), 
        'record_customer_name': fields.char('Customer product name', size=64),
        'record_frame': fields.text('Product frame'), 
        'record_color': fields.text('Product color'), 
        'record_fabric': fields.text('Product fabric'), 

        # Code:
        'record_code': fields.char('Product code', size=20), 
        'record_customer_code': fields.char('Customer code', size=20), 
        'record_ean13': fields.char('EAN 13', size=13), 
        'record_ean8': fields.char('EAN 8', size=8), 
        
        # Extra:            
        'record_q_x_pack': fields.integer('Force q. x pack'),
        
        # Static:
        'record_static_text1': fields.text('Static text 1'), 
        'record_static_text2': fields.text('Static text 2'), 
        'record_static_text3': fields.text('Static text 3'), 
        
        # -----------------------------------------------------------------
        #                         Production data:
        # -----------------------------------------------------------------
        # Line:
        'record_line': fields.char('Line', size=20, help='Production line'), 
        'record_period': fields.char('Period', size=20, 
            help='Production period YYMM  format es.: 1601'), 
        
        # Order:
        'record_order_ref': fields.char('Order ref', size=30), 
        'record_order_date': fields.date('Order date'), 

        # Counter:
        'record_counter_pack_total': fields.integer('Counter pack total',
            help='25 means: format: 1/25, 2/25... (reset every product)'),
        
        # -----------------------------------------------------------------
        # Logo:
        # -----------------------------------------------------------------
        # TODO
        # Logo Image:
        #'company_logo': fields.boolean('With company logo'),
        #'customer_logo': fields.boolean('With customer logo'),
        # Picture image:
        #'image': fields.boolean('With image logo'),
        #'drawing': fields.boolean('With drawing logo'),
        }
        
    _defaults = {
        'record_counter': lambda *x: 1,
        }
        
class LabelLabelReportJob(orm.Model):
    """ Model name: Inherit for relation fields
    """
    _inherit = 'label.label.report'
        
    _columns = {
        'job_ids': fields.one2many(
            'label.label.job', 'report_id', 'Job'),
        }    
class LabelLabel(orm.Model):
    """ Model name: Label relations
    """

    _inherit = 'label.label'
    
    _columns = {
        # TODO change in function
        'fast_ids': fields.one2many(
            'label.label.job', 'label_id', 'Job label'),
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
