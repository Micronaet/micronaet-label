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
import math
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
    
    # -------------------------------------------------------------------------
    # Utility:
    # -------------------------------------------------------------------------
    def get_placeholder_label(self, cr, uid, jobs, context=None):
        ''' Create placeholder database for print element or label
        '''
        placeholder = {}
        break_level = {'article': False, 'package': False}
        old_id = {'article': False, 'package': False}
        label_total = {'article': 0, 'package': 0}
        last_level = {'article': False, 'package': False}

        job_type = False
        for job in jobs:
            job_type = job.type   
            
            if job_type not in break_level: 
                _logger.error('No correct type of label')
                continue # end?
                         
            # Break level type (3 cases):
            current_code = job.product_id.default_code
            if job.has_address_custom:
                level = (
                    current_code, 'address', job.partner_id, job.address_id)
            elif job.has_partner_custom:
                level = (
                    current_code, 'partner', job.partner_id, False)
            else: # normal stock label
                level = (current_code, 'code', False, False)
            
            # -----------------------------------------------------------------
            # Check 3 states:
            # -----------------------------------------------------------------                
            # No break level:
            if break_level[job_type] and break_level[job_type] == level:
                label_total[job_type] += job.record_data_counter                
                old_id[job_type] = job.id # update for keep last
                
            else:
                # Break level:
                if break_level[job_type]: # only for break not first loop
                    placeholder[old_id[job_type]] = (
                        label_total[job_type],
                        last_level[job_type], # save also break level
                        )             
                        
                # Common part fist loop and break level:
                label_total[job_type] = job.record_data_counter
                break_level[job_type] = level
                last_level[job_type] = level
                old_id[job_type] = job.id
                    
        for job_type in break_level:  
            # Write last record:                          
            if break_level[job_type]: 
                placeholder[old_id[job_type]] = (
                    label_total[job_type],
                    last_level[job_type],
                    )
        return placeholder        
    
    def merge_pdf_mrp_label_jobs_demo(self, cr, uid, ids, context=None):
        ''' 1 x label job in demo mode
        '''
        ctx = context.copy()
        ctx['demo_mode'] = True
        return self.merge_pdf_mrp_label_jobs(cr, uid, ids, context=ctx)
        
    def merge_pdf_mrp_label_jobs(self, cr, uid, ids, context=None):
        ''' Merge procedure for all same label layout files:
            Context parameters:
                > collect_label: return dictionary of collected label created
        '''        
        if context is None:
            context = {}
            
        # Context parameters:    
        collect_label = context.get('collect_label', False)
        collect_label_db = {} # return database of collected label printed
        job_2_line_db = {} # convert job name in line ID
                    
        mrp = self.browse(cr, uid, ids, context=context)[0]
        user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
        
        out_path = '/home/administrator/photo/Label/pdf'
        temp_path = os.path.join(out_path, mrp.name) # '/tmp'
        os.system('mkdir -p %s' % temp_path) # Create temp folder
        
        # Batch parameter:
        pause_command = '@pause\r\n' if user.print_with_pause else ''

        # Default command:
        print_command_mask = '%s "%s" "%s"' #% user.print_label_command
        print_label_command = user.print_label_command
        
        # Custom command depend on layout:
        layout_ids = {}
        for custom in user.layout_ids:
            layout_ids[custom.layout_id.id] = custom.print_label_command
            
        label_root = user.print_label_root or ''        
        batch_file = os.path.join(out_path, 'print_%%s_%s.bat' % mrp.name)
        
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
        jobs = mrp.label_job_ids 
        #self.browse(cr, uid, ids, context=context).label_job_ids        
        # TODO sort by sequence?
        placeholder = self.get_placeholder_label(
            cr, uid, jobs, context=context)
        
        for job in jobs:
            pdf_id += 1 
            label = job.label_id
            layout = job.label_id.layout_id
            
            # Collect parameter.
            if collect_label:
                 job_2_line_db[job.id] = job.line_id.id

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
                (quantity, level) = placeholder[job.id]
                datas['placeholder_data'] = {
                    'code': job.product_id.default_code,
                    'quantity': quantity,
                    'line': job.record_data_line,
                    'period': job.record_data_period,
                    }
                # Extend for address partner break level    
                if level[1] != 'code': # partner / address break level
                    datas['placeholder_data'].update({
                        'partner': level[2].name or '',
                        'address': level[3].name if level[3] else '',
                        })
        
            # -----------------------------------------------------------------
            # Call report:
            # -----------------------------------------------------------------
            try:
                result, extension = openerp.report.render_report(
                    cr, uid, [job.id], report_name, datas, context)
            except:
                _logger.error('Error generation report: %s' % (
                    job.product_id.default_code,
                    ))
                continue
            
            if extension.upper() != 'PDF':
                #_logger.error('ODT is not PDF for report!')
                raise osv.except_osv(
                    _('Converter not working'), 
                    _('Check PDF convert, report must be in PDF not ODT!'),
                    )
                    
            # Generate file:    
            f_pdf = '%ssingle_job_%s_%s.%s' % (
                'DEMO_' if demo_mode else '',
                pdf_id,
                job.mrp_id.name,
                extension,
                )   
            filename = os.path.join(
                temp_path, 
                f_pdf,
                )
                
            report_pdf[layout].append(
                (filename, f_pdf, job)) # for merge procedure
            # XXX Aggiunto job.id per context parameters
                
            file_pdf = open(filename, 'w') # XXX binary?
            file_pdf.write(result)
            file_pdf.close()

        # ---------------------------------------------------------------------
        # Merge PDF file in one:
        # ---------------------------------------------------------------------
        for layout, files in report_pdf.iteritems():            
            # Open batch file for this format:
            batch_name = batch_file % (layout.code or layout.name)
            batch_f = open(batch_name, 'w')        
            os.chmod(batch_name, 0o777)
            batch_f.write(
                '@echo Stampa etichette stampante: %s\r\n@pause\r\n' % layout.code)
            
            pdf_filename = os.path.join(
                out_path,
                '%s%s_%s.pdf' % (
                    'DEMO_' if demo_mode else '',
                    job.mrp_id.name,
                    layout.code,
                    ))
            
            out_pdf = PdfFileWriter()
            
            # For all files:
            i = 0
            for (f, f_pdf, job) in files:            
                # -------------------------------------------------------------
                # Batch command:
                # -------------------------------------------------------------
                # Generate command:
                i += 1
                echo_command = 'echo %s. Print job: %s' % (i, f_pdf)
                if layout.id in layout_ids: # custom layout command
                    exe_command = layout_ids[layout.id]
                else:
                    exe_command = print_label_command

                print_command = print_command_mask % (
                    exe_command,
                    r'%s%s\%s' % (label_root, mrp.name, f_pdf),
                    layout.printer_id.spooler_name,
                    )
                    
                # Write in bacth file:
                batch_f.write('@%s\r\n@%s\r\n%s\r\n' % (
                    echo_command, 
                    print_command,
                    pause_command,    
                    ))

                # Context parameters:
                if collect_label:
                    #job_2_line_db
                    collect_label_db[
                        (job.type, job_2_line_db[job.id])] = (i, print_command)
                
                # -------------------------------------------------------------
                # Open and append page:
                # -------------------------------------------------------------
                in_pdf = PdfFileReader(open(f, 'rb'))
                for page_num in range(in_pdf.numPages):
                    page = in_pdf.getPage(page_num)
                    if page.getContents():
                        out_pdf.addPage(page)
                    else:
                        _logger.warning('\n' * 50)
                        _logger.warning('Remove blank page!')
                        _logger.warning('\n' * 50)

            batch_f.close()
            out_pdf.write(open(pdf_filename, 'wb'))

        # Context parameter
        if collect_label:
            return collect_label_db
        else:    
            return True
                
    def generate_label_job(self, cr, uid, ids, context=None):
        ''' Generate list of jobs label
            context extra keys:
                > sol_job: 
                    key: ID
                    value: total
        '''
        assert len(ids) == 1, 'Works only with one record a time'
        
        _logger.info('Generate job from production:')
        if context is None:
            context = {}
        
        # ---------------------------------------------------------------------
        # Lauch parameter:
        # ---------------------------------------------------------------------
        sol_job = context.get('sol_job', False) # Generate only for this job
        sol_job_mode = context.get('sol_job_mode', 'all') # Selection job mode

        # Pool used:
        job_pool = self.pool.get('label.label.job')
        partner_pool = self.pool.get('res.partner')
        note_pool = self.pool.get('note.note')
        
        mrp_proxy = self.browse(cr, uid, ids, context=context)[0]
        
        # Force generation of label  name:
        _logger.info('Regenerate frame and color name')
        self.force_product_extra_label_field(cr, uid, ids, context=context)
        
        # Remove previous label:
        _logger.info('Remove previous job')
        remove_ids = [item.id for item in mrp_proxy.label_job_ids]
        if remove_ids:
            job_pool.unlink(cr, uid, remove_ids, context=context)
            
        sequence = 0
        labels = ['article', 'package'] #'pallet', 'placeholder'
        if sol_job:
            if sol_job_mode == 'internal':
                labels = ['article']
            elif sol_job_mode == 'external':
                labels = ['package']
        
        # ---------------------------------------------------------------------
        # Sort sale order line:
        # ---------------------------------------------------------------------
        _logger.info('Sort and regenerate new')
        sorted_order_line = sorted(
            mrp_proxy.order_line_ids,
            key= lambda x: (
                x.order_id.partner_id.has_custom_label or \
                    x.order_id.destination_partner_id.has_custom_label,
                x.product_id.default_code,
                x.order_id.partner_id.name,
                x.order_id.destination_partner_id.name or False,    
                x.mrp_sequence,
                ),
            )

        for line in sorted_order_line:
            # Launch mode job:
            if sol_job and line.id not in sol_job:
                continue # Line not in job
                
            for label in labels:
                sequence += 1
                
                # -------------------------------------------------------------
                # Search 3 label depend on note system management:
                # -------------------------------------------------------------
                # TODO generate label_id with system note management!
                label_id, print_moltiplicator = \
                    note_pool.get_label_from_order_line(
                        cr, uid, line, label, context=context)
                
                report_id = False # TODO
                
                # -------------------------------------------------------------
                # Generate extra data from order, product, partner, address
                # -------------------------------------------------------------
                record_data = partner_pool.generate_job_data_from_line_partner(
                    cr, uid, line=line, context=context)
                # used for # label:
                q_x_pack = record_data.get('record_data_q_x_pack', False)
                
                if sol_job: # Job selection:
                    product_uom_qty = sol_job[line.id] # context Q passed
                    # TODO check q_x_pack extra data
                else: # Normal total production:
                    product_uom_qty = line.product_uom_qty
                    
                if label == 'article':
                    record_data_counter = product_uom_qty
                else:
                    if q_x_pack: # TODO Manage Error:
                        record_data_counter = product_uom_qty / q_x_pack
                    else:    
                        record_data_counter = product_uom_qty
                        # XXX Note: q_x_pack Remain false in job
                        
                record_data_counter *= print_moltiplicator # moltiplicator 
                
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
                    'print_moltiplicator': print_moltiplicator or 1,
                    #'error': # TODO
                    #'comment_error' # TODO
                    })
                job_pool.create(cr, uid, record_data, context=context)
        _logger.info('End job creation')
        return True
    
    def label_form_report(self, cr, uid, ids, context=None):
        ''' Open label form report
        '''
        datas = {}
        report_name = 'label_form_mrp_report'

        return {
            'type': 'ir.actions.report.xml',
            'report_name': report_name, 
            'datas': datas,
            'context': context,
            }
    
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
