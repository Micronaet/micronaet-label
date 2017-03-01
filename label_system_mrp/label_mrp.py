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
from pyPdf import PdfFileWriter, PdfFileReader


_logger = logging.getLogger(__name__)

class LabelLabelJob(orm.Model):
    """ Model name: Label job
    """
    
    _inherit = 'label.label.job'

    def open_product_label_data(self, cr, uid, ids, context=None):
        ''' Open product for label
        '''
        assert len(ids) == 1, 'Works only with one record a time'
        
        current_proxy = self.browse(cr, uid, ids, context=context)[0]
        model_pool = self.pool.get('ir.model.data')
        view_id = model_pool.get_object_reference(cr, uid, 
            'label_system', 'view_product_product_label_data_form')[1]
    
        return {
            'type': 'ir.actions.act_window',
            'name': _('Product label data'),
            'view_type': 'form',
            'view_mode': 'form,tree',
            'res_id': current_proxy.product_id.id,
            'res_model': 'product.product',
            'view_id': view_id, # False
            'views': [(view_id, 'form'), (False, 'tree')],
            'domain': [],
            'context': context,
            'target': 'current', # 'new'
            'nodestroy': False,
            }

    # -------------------------------------------------------------------------
    # Utility:
    # -------------------------------------------------------------------------
    def open_partner_view(self, cr, uid, partner_id, context=None):
        model_pool = self.pool.get('ir.model.data')
        view_id = model_pool.get_object_reference(cr, uid, 
            'partner_product_partic_label', 'view_res_partner_label_form')[1]
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Partner label setup'),
            'view_type': 'form',
            'view_mode': 'form,tree',
            'res_id': partner_id,
            'res_model': 'res.partner',
            'view_id': view_id,
            'views': [(view_id, 'form'), (False, 'tree')],
            'domain': [],
            'context': context,
            'target': 'current',
            'nodestroy': False,
            }
    
    # -------------------------------------------------------------------------
    # Button event:
    # -------------------------------------------------------------------------
    def open_partner_label_setup(self, cr, uid, ids, context=None):
        ''' Open partner setup form
        '''
        current_proxy = self.browse(cr, uid, ids, context=context)[0]
        partner_id = current_proxy.partner_id.id
        return self.open_partner_view(cr, uid, partner_id, context=context)

    def open_partner_address_label_setup(self, cr, uid, ids, context=None):
        ''' Open partner setup form
        '''
        current_proxy = self.browse(cr, uid, ids, context=context)[0]
        address_id = current_proxy.address_id.id
        return self.open_partner_view(cr, uid, address_id, context=context)

class MrpProduction(orm.Model):
    """ Model name: MrpProduction
    """
    
    _inherit = 'mrp.production'
    
    def merge_pdf_mrp_label_jobs_demo(self, cr, uid, ids, context=None):
        ''' 1 x label job in demo mode
        '''
        ctx = context.copy()
        ctx['demo_mode'] = True
        return self.merge_pdf_mrp_label_jobs(cr, uid, ids, context=ctx)
        
    def merge_pdf_mrp_label_jobs(self, cr, uid, ids, context=None):
        ''' Merge procedure for all same label layout files:
        '''        
        if context is None:
            context = {}
            
        out_path = '/home/administrator/photo/Label/pdf'
        temp_path = '/tmp'
        
        demo_mode = context.get('demo_mode', False)
        if demo_mode: 
            _logger.info('Demo mode for PDF generation')        
        else:
            _logger.info('Normal mode for PDF generation')        
        
        label_pool = self.pool.get('label.label.job')
        report_pdf = {} # database of file keep format as the same
        pdf_id = 0
        
        # ---------------------------------------------------------------------
        # Get placeholder informations:
        # ---------------------------------------------------------------------
        jobs = self.browse(cr, uid, ids, context=context).label_job_ids
        # TODO sort by sequence?

        placeholder = {}        
        break_level = {'article': False, 'package': False}
        old_id = {'article': False, 'package': False}
        label_total = {'article': 0, 'package': 0}
        
        job_type = False
        for job in jobs:
            job_type = job.type   
            
            if job_type not in break_level: 
                _logger.error('No correct type of label')
                         
            current_code = job.product_id.default_code
            level = (current_code, )
            if break_level[job_type] == level:
                label_total[job_type] += job.record_data_counter                
                old_id[job_type] = job.id # update for keep last
            else: # change
                placeholder[old_id[job_type]] = label_total[job_type]
                label_total[job_type] = job.record_data_counter
                break_level[job_type] = level
                old_id[job_type] = job.id
                
        if jobs: # Write last
            placeholder[old_id['article']] = label_total['article']
            placeholder[old_id['package']] = label_total['package']

        for job in jobs:
            pdf_id += 1 
            label = job.label_id
            layout = job.label_id.layout_id
            
            # Database of same layut pdf report: 
            if layout not in report_pdf:
                report_pdf[layout] = []
                
            report_name = label.report_id.report_name
            datas = {
                'record_ids': [job.id],
                'model': 'label.label.job',
                'active_id': job.id,
                'active_ids': [job.id],
                'demo_mode': demo_mode, # XXX set as demo mode (1x)
                }
            if job.id in placeholder:
                datas['placeholder_data'] = {
                    'code': job.product_id.default_code,
                    'quantity': placeholder[job.id],
                    'line': job.record_data_line,
                    'period': job.record_data_period,
                    }
        
            # -----------------------------------------------------------------
            # Call report:            
            # -----------------------------------------------------------------
            result, extension = openerp.report.render_report(
                cr, uid, [job.id], report_name, datas, context)
            
            if extension.upper() != 'PDF':
                #_logger.error('ODT is not PDF for report!')
                raise osv.except_osv(
                    _('Converter not working'), 
                    _('Check PDF confert, report must be in PDF not ODT!'),
                    )
                    
            # Generate file:    
            filename = os.path.join(
                temp_path, 
                '%ssingle_job_%s_%s.%s' % (
                    'DEMO_' if demo_mode else '',
                    pdf_id,
                    job.mrp_id.name,
                    extension,
                ))
            report_pdf[layout].append(filename) # for merge procedure
                
            file_pdf = open(filename, 'w') # XXX binary?
            file_pdf.write(result)
            file_pdf.close()

        # ---------------------------------------------------------------------
        # Merge PDF file in one:
        # ---------------------------------------------------------------------
        for layout, files in report_pdf.iteritems():
            pdf_filename = os.path.join(
                out_path,
                '%s%s_%s.pdf' % (
                    'DEMO_' if demo_mode else '',
                    job.mrp_id.name,
                    layout.code,
                    ))
            
            out_pdf = PdfFileWriter()
            # For all files:
            for f in files:
                # Open and append page:
                in_pdf = PdfFileReader(open(f, 'rb'))
                [out_pdf.addPage(in_pdf.getPage(page_num)) for \
                    page_num in range(in_pdf.numPages)]
        
            out_pdf.write(open(pdf_filename, 'wb'))
        return True
                
    def generate_label_job(self, cr, uid, ids, context=None):
        ''' Generate list of jobs label
        '''
        assert len(ids) == 1, 'Works only with one record a time'
        
        if context is None:
            context = {}
            
        # Pool used:
        job_pool = self.pool.get('label.label.job')
        partner_pool = self.pool.get('res.partner')
        note_pool = self.pool.get('note.note')
        
        mrp_proxy = self.browse(cr, uid, ids, context=context)[0]
        
        # Remove previous label:
        remove_ids = [item.id for item in mrp_proxy.label_job_ids]
        if remove_ids:
            job_pool.unlink(cr, uid, remove_ids, context=context)
            
        sequence = 0
        labels = ['article', 'package'] #'pallet', 'placeholder'
        
        sorted_order_line = sorted(
            mrp_proxy.order_line_ids,
            key= lambda x: (
                x.order_id.partner_id.has_custom_label or \
                    x.order_id.destination_partner_id.has_custom_label,
                x.mrp_sequence),
            )
        for line in sorted_order_line:
            for label in labels:
                sequence += 1
                
                # -------------------------------------------------------------
                # Search 3 label depend on note system management:
                # -------------------------------------------------------------
                # TODO generate label_id with system note management!
                label_id = note_pool.get_label_from_order_line(
                    cr, uid, line, label, context=context)
                report_id = False # TODO
                
                # -------------------------------------------------------------
                # Generate extra data from order, product, partner, address
                # -------------------------------------------------------------
                record_data = partner_pool.generate_job_data_from_line_partner(
                    cr, uid, line=line, context=context)
                # used for # label:
                q_x_pack = record_data.get('record_data_q_x_pack', False)
                
                if label == 'article':
                    record_data_counter = line.product_uom_qty
                else:
                    if q_x_pack: # TODO Manage Error:
                        record_data_counter = line.product_uom_qty / q_x_pack
                    else:    
                        record_data_counter = line.product_uom_qty
                        # XXX Note: q_x_pack Remain false in job
                
                # -------------------------------------------------------------
                # Create Job:            
                # -------------------------------------------------------------
                # Integrate with line information:
                record_data.update({
                    'sequence': sequence,
                    'label_id': label_id, # label.label
                    'report_id': report_id, #label.label.report
                    #'lang_id':,
                    'demo': False,
                    'fast': False,
                    
                    'record_data_counter': record_data_counter,

                    #'error': # TODO
                    #'comment_error' # TODO
                    })
                job_pool.create(cr, uid, record_data, context=context)
        return True
    
    def label_check_report(self, cr, uid, ids, context=None):
        ''' Report for check error label
        '''
        datas = {}
        report_name = 'check_label_mrp_report'

        return {
            'type': 'ir.actions.report.xml',
            'report_name': report_name, 
            'datas': datas,
            'context': context,
            }
        
    _columns = {
        'label_job_ids': fields.one2many(
            'label.label.job', 'mrp_id', 
            'Label Job'),
        }
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
