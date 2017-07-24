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
class LabelPrinters(orm.Model):
    """ Model name: Label printers
    """

    _name = 'label.printer'
    _description = 'Label printer'

    _columns = {    
        'name': fields.char('Label format', size=64, required=True),
        'spooler_name': fields.char('Spooler name', size=80, required=True), 
        }    

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
        
        # Printer:
        'printer_id': fields.many2one(
            'label.printer', 'Printer', required=True),
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
                    partner_id = False    
            
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
        job_ids = job_pool.search(cr, uid, [
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
        'lang_id': fields.many2one('res.lang', 'Lang'),# TODO remove?
        'demo': fields.boolean('Demo'), 
        'fast': fields.boolean('Fast label', 
            help='Job that is never cleaned, used sometimes for print direct'),
        'print_moltiplicator': fields.integer('Print multiplicator'),
        
        'has_partner_custom': fields.boolean('Partner custom',
            help='Has partner custom data or label'),
        'has_address_custom': fields.boolean('Address custom',
            help='Has address custom data or label'),

        # Layout reference:
        'layout_id': fields.related(
            'label_id', 'layout_id', 
            type='many2one', relation='label.layout', 
            string='Layout', readonly=True),
        'type': fields.related(
            'label_id', 'type', selection=label_type,
            type='selection', string='Type', readonly=True),
                
        # -----------------------------------------------------------------
        #                           Linked object:
        # -----------------------------------------------------------------
        'product_id': fields.many2one('product.product', 'Product'),
        'partner_id': fields.many2one('res.partner', 'Partner', 
            domain=[('is_company', '=', True), ('is_address', '=', False)]),
        'address_id': fields.many2one('res.partner', 'Address', 
            domain=[('is_address', '=', True)]),
        'order_id': fields.many2one('sale.order', 'Order'),
        'line_id': fields.many2one('sale.order.line', 'Order line'),
        'mrp_id': fields.many2one('mrp.production', 'Production'),

        # ---------------------------------------------------------------------
        #                               RECORD:
        # ---------------------------------------------------------------------    
        'record_data_counter': fields.integer('Counter', required=True, 
            help='Number of label printed'),
        
        # ---------------------------------------------------------------------
        #                         PRODUCT DATA RECORD:
        # ---------------------------------------------------------------------
        # -------------
        # Label string:
        # -------------
        # Anagrafic text:
        'record_string_code': fields.char(
            'Label company code', 
            size=40, translate=True),
        'record_string_code_partner': fields.char('Label partner code', 
            size=40, translate=True),
        'record_string_description': fields.char(
            'Label company description', 
            size=40, translate=True),
        'record_string_description_partner': fields.char(
            'Label partner description', 
            size=40, translate=True),
        'record_string_frame': fields.char('Label frame',
            size=40, translate=True),
        'record_string_fabric': fields.char('Label fabric', 
            size=40, translate=True),

        # Anagrafic numeric:        
        'record_string_q_x_pack': fields.char('Label Q. x pack', 
            size=40, translate=True),
        'record_string_q_x_pallet': fields.char('Label Q. x pallet', 
            size=40, translate=True),
        'record_string_dimension': fields.char('Label dimension', 
            size=40, translate=True),
        'record_string_volume': fields.char('Label volume', 
            size=40, translate=True),
        'record_string_weight_net': fields.char('Label weight net', 
            size=40, translate=True),
        'record_string_weight_lord': fields.char('Label weight lord', 
            size=40, translate=True),
        'record_string_parcel': fields.char('Label parcel', 
            size=40, translate=True),
        'record_string_price': fields.char('Label price', 
            size=40, translate=True),
        #'label_string_price_uom':

        # EAN data:
        #'record_string_ean13' 'record_string_ean8'
        
        # Production:
        'record_string_line': fields.char('Label production line', 
            size=40, translate=True),
        'record_string_period': fields.char('Label period', 
            size=40, translate=True),
        'record_string_lot': fields.char('Label lot', 
            size=40, translate=True),
        'record_string_mrp_date': fields.char('Label prod. date', 
            size=40, translate=True),
        
        # Order:
        'record_string_order_ref': fields.char('Label order ref', 
            size=40, translate=True), # customer
        'record_string_order_date': fields.char('Label order date', 
            size=40, translate=True),
        'record_string_order_deadline': fields.char('Label order deadline', 
            size=40, translate=True),
        'record_string_destination_code': fields.char(
            'Label destination code', 
            size=40, translate=True),
            
        # Image:
        #'record_string_company_logo' 'record_string_partner_logo'
        #'record_string_linedrawing' 'record_string_product_image'
               
        # Counter:            
        'record_string_counter_pack_total': fields.char('Label counter pack', 
            size=40, translate=True),   

        # ---------------
        # Required field:
        # ---------------
        # Anagrafic text:
        'record_print_code': fields.boolean('Print company code'),
        'record_print_code_partner': fields.boolean('Print partner code'),
        'record_print_description': fields.boolean(
            'Print company description'),
        'record_print_description_partner': fields.boolean(
            'Print partner description'),
        'record_print_frame': fields.boolean('Print frame'), # TODO add
        'record_print_fabric': fields.boolean('Print fabric'), # TODO add

        # Anagrafic numeric:
        'record_print_q_x_pack': fields.boolean('Print Q. x pack'),
        'record_print_q_x_pallet': fields.boolean('Print Q. x pallet'),#TODO add
        'record_print_dimension': fields.boolean('Print dimension'),
        'record_print_volume': fields.boolean('Print volume'),
        'record_print_weight_net': fields.boolean('Print weight net'),
        'record_print_weight_lord': fields.boolean('Print weight lord'),
        'record_print_parcel': fields.boolean('Print parcel'),
        'record_print_price': fields.boolean('Print price'),
        'record_print_price_uom': fields.boolean('Print price uom'), # TODO add

        # EAN data:
        'record_print_ean13': fields.boolean('Print EAN13'),
        'record_print_ean8': fields.boolean('Print EAN8'),
        
        # Production:
        'record_print_line': fields.boolean('Print production line'),
        'record_print_period': fields.boolean('Print period',
            help='Production period YYMM  format es.: 1601'),
        'record_print_lot': fields.boolean('Print lot'),
        'record_print_mrp_date': fields.boolean('Print prod. date',
            help='Production date'),
        
        # Order:
        'record_print_order_ref': fields.boolean('Print order ref'), # customer
        'record_print_order_date': fields.boolean('Print order date'),
        'record_print_order_deadline': fields.boolean('Print order deadline'),
        'record_print_destination_code': fields.boolean(
            'Print destination code'),
            
        # Image:
        'record_print_company_logo': fields.boolean('Print company logo'),
        'record_print_partner_logo': fields.boolean('Print partner logo'),
        'record_print_linedrawing': fields.boolean('Print line drawing'), 
        #'label_print_product_image': fields.boolean('Print product mage')
        
        # Counter:            
        'record_print_counter_pack_total': fields.boolean('Print counter pack',
            help='For print in label: 1/25, 2/25... (reset every product)'),  

        # -----------
        # Data field:
        # -----------
        # Anagrafic text:
        'record_data_code': fields.char('Company code', size=30),
        'record_data_code_partner': fields.char('Partner code', size=30),
        'record_data_description': fields.char(
            'company description', size=60),
        'record_data_description_partner': fields.char(
            'Partner description', size=60),
        'record_data_frame': fields.char('Frame', size=50), # TODO add
        'record_data_fabric': fields.char('Fabric', size=50), # TODO add

        # Anagrafic numeric:
        # TODO change float
        'record_data_q_x_pack': fields.char('Q. x pack', size=10),
        'record_data_q_x_pallet': fields.char('Q. x pallet', size=10),
        'record_data_dimension': fields.char('Dimension', size=45),
        'record_data_volume': fields.char('Volume', size=10),
        'record_data_weight_net': fields.char('Weight net', size=10),
        'record_data_weight_lord': fields.char('Weight lord', size=10),
        'record_data_parcel': fields.char('Parcel', size=10),
        'record_data_price': fields.char('Price', size=15),
        'record_data_price_uom': fields.char('Price uom', size=10),

        # EAN data:
        'record_data_ean13_mono': fields.char('EAN13 single', size=13),
        'record_data_ean13': fields.char('EAN13', size=13),
        'record_data_ean8_mono': fields.char('EAN8 single', size=8),
        'record_data_ean8': fields.char('EAN8', size=8),
        
        # Production:
        'record_data_line': fields.char('Production line', size=10),
        'record_data_period': fields.char('Period', size=10,
            help='Production period YYMM  format es.: 1601'),
        'record_data_lot': fields.char('Lot', size=15),
        'record_data_mrp_date': fields.char('Prod. date', size=14,
            help='Production date'),
        
        # Order:
        'record_data_order_ref': fields.char('Order ref', size=50), # customer
        'record_data_order_date': fields.char('Order date', size=10),
        'record_data_order_deadline': fields.char('Order deadline', size=10),
        'record_data_destination_code': fields.char(
            'Destination code', size=20),
            
        # Image:
        # XXX Note: used related elements
        #record_data_company_logo record_data_partner_logo
        #record_data_linedrawing label_print_product_image        
        
        # Extra images:
        # XXX Note: used related elements
        #record_data_extra_image_ids
        
        # Static text:
        'record_data_text1': fields.text('Static text 1'), 
        'record_data_text2': fields.text('Static text 2'), 
        'record_data_text3': fields.text('Static text 3'), 
        
        # TODO manage error and comment for error
        }
        
    _defaults = {
        'fast': lambda *x: True, #for manual creation
        'record_data_counter': lambda *x: 1,
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
        'label_image': fields.binary('Label image', 
            help='Image logo used for label print'),
        }

class LabelLayoutUser(orm.Model):
    """ Model name: LabelLayoutUser
    """    
    _name = 'label.layout.user'
    _description = 'User layout'
    _rec_name = 'print_label_command'
    _order = 'print_label_command'
    
    _columns = {
        'print_label_command': fields.char(
            'Print command', size=100, required=True),
        'user_id': fields.many2one('res.users', 'User'),
        'layout_id': fields.many2one(
            'label.layout', 'Layout', required=True),
        }

class ResUsers(orm.Model):
    """ Model name: ResUsers
    """    
    _inherit = 'res.users'

    _columns = {
        'print_label_command': fields.char('Print default command', size=100),
        'print_label_root': fields.char('Print root', size=100),
        'print_with_pause': fields.boolean(
            'Print pause', help='Insert batch pause'),
        'layout_ids': fields.one2many(
            'label.layout.user', 'user_id', 'Command for layout'),
        }
    
    _defaults = {
        'print_with_pause': lambda *x: True,
        }    
       
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
