﻿#!/usr/bin/env python
import os
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
import pyfits


__doc__ = """
Graphical Interface for WebbPSF 

Developed in wxpython by Marshall Perrin

Some code based on/borrowed from Scamp by Klaus Pontoppidan

"""

try:
    import wx, wx.html
except ImportError:
    raise ImportError,"The wxPython module is required to run this program."


import logging
import logging
_log = logging.getLogger('webbpsf')
#_log.setLevel(logging.INFO)





try:
    import pysynphot
    _HAS_PYSYNPHOT=True
except:
    _HAS_PYSYNPHOT=False


import poppy
import webbpsf_core

class WebbPSF_GUI(wx.Frame):
    """ A GUI for the PSF Simulator 

    Documentation TBD!

    """
    def __init__(self, parent=None, id=-1, title="WebbPSF: JWST PSF Calculator"): 
        wx.Frame.__init__(self,parent,id=id,title=title)
        self.parent=parent
        opdserver=None
        self.log_window=None
        # init the object and subobjects
        self.instrument = {}
        self.widgets = {}
        self.vars = {}
        self.advanced_options = {'parity': 'any', 'force_coron': False, 'no_sam': False, 'psf_vmin': 1e-8, 'psf_vmax': 1.0, 'psf_scale': 'log', 'psf_cmap_str': 'Jet (blue to red)' , 'psf_normalize': 'Total', 'psf_cmap': matplotlib.cm.jet}
        insts = ['NIRCam', 'NIRSpec','NIRISS', 'MIRI', 'FGS']
        for i in insts:
            self.instrument[i] = webbpsf_core.Instrument(i)
        #invoke link to ITM server if provided?
        if opdserver is not None:
            self._enable_opdserver = True
            self._opdserver = opdserver
        else:
            self._enable_opdserver = False

        
        # create widgets & run
        self._create_widgets_wx()
        #self.root.update()

    def _add_labeled_dropdown(self, name, parent, parentsizer, label="Entry:", choices=None, default=0, width=5, position=(0,0), columnspan=1, **kwargs):
        "convenient wrapper for adding a Combobox"

        mylabel = wx.StaticText(parent, -1,label=label)
        parentsizer.Add( mylabel, position,  (1,1), wx.EXPAND|wx.ALIGN_CENTER_VERTICAL)

        if choices is None:
            try:
                choices = self.values[name]
            except:
                choices = ['Option A','Option B']

        if isinstance(default,int):
            value = choices[default]
        else:
            value=default

        mycombo = wx.ComboBox(parent, -1,value=value, choices=choices, style=wx.CB_DROPDOWN|wx.CB_READONLY)
        parentsizer.Add( mycombo, (position[0],position[1]+1),  (1,columnspan), wx.EXPAND)

        self.widgets[name] = mycombo
 

    def _add_labeled_entry(self, name, parent, parentsizer, label="Entry:", value=None, format="%.2g", 
            width=5, position=(0,0), postlabel=None, **kwargs):
        "convenient wrapper for adding an Entry"
        mylabel = wx.StaticText(parent, -1,label=label)
        parentsizer.Add( mylabel, position,  (1,1), wx.EXPAND)


        if value is None:
            try:
                value=format % self.input_options[name]
            except:
                value=""

        mytext = wx.TextCtrl(parent, -1,value=value)
        parentsizer.Add( mytext, (position[0],position[1]+1),  (1,1), wx.EXPAND)

        self.widgets[name] = mytext

        if postlabel is not None:
            mylabel2 = wx.StaticText(parent, -1,label=postlabel)
            parentsizer.Add( mylabel2, (position[0],position[1]+2),  (1,1), wx.EXPAND)



    def _create_widgets_wx(self):
        """Create a nice GUI using the enhanced widget set provided by 
        the ttk extension to Tkinter, available in Python 2.7 or newer
        """
        #---- create the GUIs
        insts = ['NIRCam', 'NIRSpec','NIRISS', 'MIRI',  'FGS']
        self.sb =self.CreateStatusBar()

        menuBar = WebbPSFMenuBar(self)
        self.SetMenuBar(menuBar)

        top_panel = wx.Panel(self)


        topSizer = wx.BoxSizer(wx.VERTICAL)


        #frame = ttk.Frame(self.root)
        #frame = ttk.Frame(self.root, padx=10,pady=10)

        #ttk.Label(frame, text='James Webb PSF Calculator' ).grid(row=0)

        #===== source properties panel ======
        sb1 = wx.StaticBox(top_panel, label='Source Properties')
        sb1Sizer = wx.StaticBoxSizer(sb1,wx.VERTICAL)


        if _HAS_PYSYNPHOT:
            spectrumPanel = wx.Panel(top_panel)
            spectrumSizer = wx.GridBagSizer()

            self._add_labeled_dropdown("SpType", spectrumPanel,spectrumSizer, label='    Spectral Type:', 
                    choices=poppy.specFromSpectralType("",return_list=True), default='G0V', 
                    position=(0,0))
            self.ButtonPlotSpec = wx.Button(spectrumPanel, label='Plot Spectrum')
            self.Bind(wx.EVT_BUTTON, self.ev_plotspectrum, self.ButtonPlotSpec)
            spectrumSizer.Add(self.ButtonPlotSpec, (0,3),(1,1))
            spectrumSizer.AddGrowableCol(2)

            spectrumPanel.SetSizerAndFit(spectrumSizer)
            sb1Sizer.Add(spectrumPanel, 0, wx.ALL|wx.EXPAND, 2)

        posPanel = wx.Panel(top_panel)
        posSizer = wx.GridBagSizer()
        r=0
        self._add_labeled_entry("source_off_r", posPanel,posSizer, label='    Source Position: r=', value='0.0',  position=(r,0))
        self._add_labeled_entry("source_off_theta", posPanel,posSizer, label='arcsec,  PA=', value='0', position=(r,2))
        posPanel.SetSizerAndFit(posSizer)
        sb1Sizer.Add(posPanel,0, wx.ALL|wx.EXPAND, 2)


        #===== instruments panels ========
        nb = wx.Notebook(top_panel)
        for iname in insts:
            inst_panel = wx.Panel(nb)
            inst_panel.WebbPSFInstrumentName = iname
            panelSizer = wx.GridBagSizer()


            panelSizer.Add(wx.StaticText(inst_panel, label='Configuration Options for '+iname+"     "), (0,0),(1,3), flag=wx.ALIGN_LEFT)

            instButton = wx.Button(inst_panel, label='Display Optics')
            panelSizer.Add(instButton, (0,4),(1,2), flag=wx.ALIGN_RIGHT)
            self.Bind(wx.EVT_BUTTON, self.ev_displayOptics, instButton)


            self._add_labeled_dropdown(iname+"_filter", inst_panel,panelSizer, label='    Filter:', choices=self.instrument[iname].filter_list, 
                default=self.instrument[iname].filter, width=12, position=(1,0))

            if len(self.instrument[iname].image_mask_list) >0 :
                masks = self.instrument[iname].image_mask_list
                masks.insert(0, "")
 
                self._add_labeled_dropdown(iname+"_coron", inst_panel,panelSizer, label='    Coron:', choices=masks,  width=12, position=(2,0))


            if len(self.instrument[iname].image_mask_list) >0 :
                masks = self.instrument[iname].pupil_mask_list
                masks.insert(0, "")
                self._add_labeled_dropdown(iname+"_pupil", inst_panel,panelSizer, label='    Pupil:', choices=masks,  width=12, position=(3,0))

                fr2 = wx.Panel(inst_panel) 
                fr2Sizer = wx.GridBagSizer()
                self._add_labeled_entry(iname+"_pupilshift_x", fr2,fr2Sizer, label='  pupil shift in X:', value='0', width=3, position=(0,4))
                self._add_labeled_entry(iname+"_pupilshift_y", fr2,fr2Sizer, label=' Y:', value='0', width=3, position=(0,6))

                fr2Sizer.Add(wx.StaticText(fr2, label='% of pupil' ), (0,8), (1,1))
                fr2.SetSizerAndFit(fr2Sizer)

                panelSizer.Add(fr2, (3,3),(1,3))

            

            panelSizer.Add(wx.StaticText(inst_panel, label='Configuration Options for the Telescope (OTE) '), (5,0),(1,5), flag=wx.ALIGN_LEFT)
            opdPanel = wx.Panel(inst_panel)
            opdSizer=wx.GridBagSizer()
            opd_list =  self.instrument[iname].opd_list
            opd_list.insert(0,"Zero OPD (perfect)")
            if self._enable_opdserver:
                opd_list.append("OPD from ITM Server")
            default_opd = self.instrument[iname].pupilopd if self.instrument[iname].pupilopd is not None else "Zero OPD (perfect)"

            self._add_labeled_dropdown(iname+"_opd", opdPanel,opdSizer, label='    OPD File:', choices=opd_list, default=default_opd, width=21, position=(0,0))

            self._add_labeled_dropdown(iname+"_opd_i", opdPanel,opdSizer, label=' # ', choices= [str(i) for i in range(10)], width=3, position=(0,2))

            self.widgets[iname+"_opd_label"] = wx.StaticText(opdPanel, label=' 0 nm RMS            ' )
            opdSizer.Add(self.widgets[iname+"_opd_label"], (0,5),(1,1))
            opdSizer.AddGrowableCol(4)

            instDispButton = wx.Button(opdPanel,label='Display OPD')
            opdSizer.Add(instDispButton, (0,6),(1,1), flag=wx.ALIGN_RIGHT)
            self.Bind(wx.EVT_BUTTON, self.ev_displayOPD, instDispButton)

            opdPanel.SetSizerAndFit(opdSizer)

            panelSizer.Add(opdPanel, (6,0), (1,6), flag=wx.EXPAND|wx.ALL)




            panelSizer.AddGrowableCol(2)
            panelSizer.AddGrowableRow(4)

            inst_panel.SetSizerAndFit(panelSizer)
        
            nb.AddPage(inst_panel, iname)

        self.widgets['tabset'] = nb
        #===== Calculation Options ======

        sb3 = wx.StaticBox(top_panel, label='Calculation Options')
        sb3Sizer = wx.StaticBoxSizer(sb3,wx.VERTICAL)

        calcPanel = wx.Panel(top_panel)
        calcSizer = wx.GridBagSizer()


        r=0 
        self._add_labeled_entry('FOV', calcPanel,calcSizer, label='Field of View:',  value='5', postlabel='arcsec/side', position=(0,0))
        r+=1
        self._add_labeled_entry('detector_oversampling', calcPanel,calcSizer, label='Output Oversampling:',  width=3, value='2', postlabel='x finer than instrument pixels       ', position=(r,0))




        r+=1
        self._add_labeled_entry('fft_oversampling', calcPanel,calcSizer, label='Coronagraph FFT Oversampling:',  width=3, value='2', postlabel='x finer than Nyquist', position=(r,0))
        r+=1
        self._add_labeled_entry('nlambda', calcPanel,calcSizer, label='# of wavelengths:',  width=3, value='', position=(r,0), postlabel='Leave blank for autoselect')
        r+=1

        self._add_labeled_dropdown("jitter", calcPanel,calcSizer, label='Jitter model:', choices=  ['Just use OPDs' ], width=20, position=(r,0), columnspan=2)
        r+=1
        output_options=['Oversampled PSF only', 'Oversampled + Detector Res. PSFs', 'Mock full image from JWST DMS']
        self._add_labeled_dropdown("output_format", calcPanel,calcSizer, label='Output Format:', choices=  ['Oversampled image','Detector sampled image','Both as FITS extensions', 'Mock JWST DMS Output' ], width=30, position=(r,0), columnspan=2)

        calcPanel.SetSizerAndFit(calcSizer)
        sb3Sizer.Add(calcPanel,0, wx.ALL|wx.EXPAND, 2)


        #====== button bar ===========

        bbar = wx.Panel(top_panel)
        bbarSizer = wx.BoxSizer(wx.HORIZONTAL)
        self.ButtonCompute = wx.Button(bbar, label='Compute PSF')
        bbarSizer.Add(self.ButtonCompute, 1, flag=wx.ALL|wx.EXPAND, border=3)
        self.ButtonSavePSF = wx.Button(bbar, label='Save PSF As...')
        self.ButtonDisplayPSF = wx.Button(bbar, label='Display PSF')
        self.ButtonDisplayProf =wx.Button( bbar, label='Display Profiles')
        self.ButtonSavePSF.Enable(False)
        self.ButtonDisplayPSF.Enable(False)
        self.ButtonDisplayProf.Enable(False)
        self.ButtonOptions = wx.Button(bbar, label='More Options...')
        self.ButtonQuit = wx.Button(bbar, label='Quit')
        self.widgets['Display PSF'] = self.ButtonDisplayPSF
        self.widgets['Display profiles'] = self.ButtonDisplayProf
        self.widgets['Save PSF As...'] = self.ButtonSavePSF
        bbarSizer.Add(self.ButtonSavePSF , 1, flag=wx.ALL|wx.EXPAND, border=3)
        bbarSizer.Add(self.ButtonDisplayPSF , 1, flag=wx.ALL|wx.EXPAND, border=3)
        bbarSizer.Add(self.ButtonDisplayProf , 1, flag=wx.ALL|wx.EXPAND, border=3)
        bbarSizer.Add(self.ButtonOptions , 1, flag=wx.ALL|wx.EXPAND, border=3)
        bbarSizer.Add(self.ButtonQuit , 1, flag=wx.ALL|wx.EXPAND, border=3)
        bbar.SetSizerAndFit(bbarSizer)

        self.Bind(wx.EVT_BUTTON, self.ev_calcPSF, self.ButtonCompute)
        self.Bind(wx.EVT_BUTTON, self.ev_displayPSF, self.ButtonDisplayPSF)
        self.Bind(wx.EVT_BUTTON, self.ev_displayProfiles, self.ButtonDisplayProf)
        self.Bind(wx.EVT_BUTTON, self.ev_SaveAs, self.ButtonSavePSF)
        self.Bind(wx.EVT_BUTTON, self.ev_options, self.ButtonOptions)
        self.Bind(wx.EVT_BUTTON, self.OnClose, self.ButtonQuit)


        #==== Add items into top sizer of window
        topSizer.Add(sb1Sizer, 5, flag=wx.EXPAND|wx.ALL, border=10)
        topSizer.Add(nb, 10, flag=wx.EXPAND|wx.ALL, border=6)
        topSizer.Add(sb3Sizer, 9, flag=wx.EXPAND|wx.ALL, border=10)
        topSizer.Add(bbar, 0, flag=wx.EXPAND|wx.ALL, border=10)

        top_panel.SetSizerAndFit(topSizer)
        topSizer.Fit(self)
        self.SetSizeHints(self.GetSize().x,self.GetSize().y,-1,-1 ); #can get bigger but not smaller




        self.Bind(wx.EVT_CLOSE, self.OnClose)

        self.Center() # or centre? 
        self.Show(True)
        return

    def old_create_widgets(self):

        #-- instruments
        lf = ttk.LabelFrame(frame, text='Instrument Config')
        notebook = ttk.Notebook(lf)
        self.widgets['tabset'] = notebook
        notebook.pack(fill='both')
        for iname,i in zip(insts, range(len(insts))):
            page = ttk.Frame(notebook)
            notebook.add(page,text=iname) 
            notebook.select(i)  # make it active
            self.widgets[notebook.select()] = iname # save reverse lookup from meaningless widget "name" to string name
            if iname =='NIRCam':
                lframe = ttk.Frame(page)

                ttk.Label(lframe, text='Configuration Options for '+iname+',     module: ').grid(row=0, column=0, sticky='W')
                mname='NIRCam module'
                self.vars[mname] = tk.StringVar()
                self.widgets[mname] = ttk.Combobox(lframe, textvariable=self.vars[mname], width=2, state='readonly')
                self.widgets[mname].grid(row=0,column=1, sticky='W')
                self.widgets[mname]['values'] = ['A','B']
                self.widgets[mname].set('A')

                lframe.grid(row=0, columnspan=2, sticky='W')
            else:
                ttk.Label(page, text='Configuration Options for '+iname+"                      ").grid(row=0, columnspan=2, sticky='W')

            ttk.Button(page, text='Display Optics', command=self.ev_displayOptics ).grid(column=2, row=0, sticky='E', columnspan=3)




            #if hasattr(self.instrument[iname], 'ifu_wavelength'):
            if iname == 'NIRSpec' or iname =='MIRI':
                fr2 = ttk.Frame(page)
                #label = 'IFU' if iname !='TFI' else 'TF'
                ttk.Label(fr2, text='   IFU wavelen: ', state='disabled').grid(row=0, column=0)
                self.widgets[iname+"_ifu_wavelen"] = ttk.Entry(fr2, width=5) #, disabledforeground="#A0A0A0")
                self.widgets[iname+"_ifu_wavelen"].insert(0, str(self.instrument[iname].monochromatic))
                self.widgets[iname+"_ifu_wavelen"].grid(row=0, column=1)
                self.widgets[iname+"_ifu_wavelen"].state(['disabled'])
                ttk.Label(fr2, text=' um' , state='disabled').grid(row=0, column=2)
                fr2.grid(row=1,column=2, columnspan=6, sticky='E')

                iname2 = iname+"" # need to make a copy so the following lambda function works right:
                self.widgets[iname+"_filter"].bind('<<ComboboxSelected>>', lambda e: self.ev_update_ifu_label(iname2))


            if len(self.instrument[iname].image_mask_list) >0 :
                masks = self.instrument[iname].image_mask_list
                masks.insert(0, "")
 
                self._add_labeled_dropdown(iname+"_coron", page, label='    Coron:', values=masks,  width=12, position=(2,0), sticky='W')


            if len(self.instrument[iname].image_mask_list) >0 :
                masks = self.instrument[iname].pupil_mask_list
                masks.insert(0, "")
                self._add_labeled_dropdown(iname+"_pupil", page, label='    Pupil:', values=masks,  width=12, position=(3,0), sticky='W')

                fr2 = ttk.Frame(page)
                self._add_labeled_entry(iname+"_pupilshift_x", fr2, label='  pupil shift in X:', value='0', width=3, position=(3,4), sticky='W')
                self._add_labeled_entry(iname+"_pupilshift_y", fr2, label=' Y:', value='0', width=3, position=(3,6), sticky='W')

                ttk.Label(fr2, text='% of pupil' ).grid(row=3, column=8)
                fr2.grid(row=3,column=3, sticky='W')


            ttk.Label(page, text='Configuration Options for the OTE').grid(row=4, columnspan=2, sticky='W')
            fr2 = ttk.Frame(page)

            opd_list =  self.instrument[iname].opd_list
            opd_list.insert(0,"Zero OPD (perfect)")
            #if os.getenv("WEBBPSF_ITM") or 1:  
            if self._enable_opdserver:
                opd_list.append("OPD from ITM Server")
            default_opd = self.instrument[iname].pupilopd if self.instrument[iname].pupilopd is not None else "Zero OPD (perfect)"
            self._add_labeled_dropdown(iname+"_opd", fr2, label='    OPD File:', values=opd_list, default=default_opd, width=21, position=(0,0), sticky='W')

            self._add_labeled_dropdown(iname+"_opd_i", fr2, label=' # ', values= [str(i) for i in range(10)], width=3, position=(0,2), sticky='W')

            self.widgets[iname+"_opd_label"] = ttk.Label(fr2, text=' 0 nm RMS            ', width=35)
            self.widgets[iname+"_opd_label"].grid( column=4,sticky='W', row=0)

            self.widgets[iname+"_opd"].bind('<<ComboboxSelected>>', 
                    lambda e: self.ev_update_OPD_labels() )
                    # The below code does not work, and I can't tell why. This only ever has iname = 'FGS' no matter which instrument.
                    # So instead brute-force it with the above to just update all 5. 
                    #lambda e: self.ev_update_OPD_label(self.widgets[iname+"_opd"], self.widgets[iname+"_opd_label"], iname) )
            ttk.Button(fr2, text='Display', command=self.ev_displayOPD).grid(column=5,sticky='E',row=0)

            fr2.grid(row=5, column=0, columnspan=4,sticky='S')



            # ITM interface here - build the widgets now but they will be hidden by default until the ITM option is selected
            fr2 = ttk.Frame(page)
            self._add_labeled_entry(iname+"_coords", fr2, label='    Source location:', value='0, 0', width=12, position=(1,0), sticky='W')
            units_list = ['V1,V2 coords', 'detector pixels']
            self._add_labeled_dropdown(iname+"_coord_units", fr2, label='in:', values=units_list, default=units_list[0], width=11, position=(1,2), sticky='W')
            choose_list=['', 'SI center', 'SI upper left corner', 'SI upper right corner', 'SI lower left corner', 'SI lower right corner']
            self._add_labeled_dropdown(iname+"_coord_choose", fr2, label='or select:', values=choose_list, default=choose_list[0], width=21, position=(1,4), sticky='W')


            ttk.Label(fr2, text='    ITM output:').grid(row=2, column=0, sticky='W')
            self.widgets[iname+"_itm_output"] = ttk.Label(fr2, text='    - no file available yet -')
            self.widgets[iname+"_itm_output"].grid(row=2, column=1, columnspan=4, sticky='W')
            ttk.Button(fr2, text='Access ITM...', command=self.ev_launch_ITM_dialog).grid(column=5,sticky='E',row=2)


            fr2.grid(row=6, column=0, columnspan=4,sticky='SW')
            self.widgets[iname+"_itm_coords"] = fr2


        self.ev_update_OPD_labels()
        lf.grid(row=2, sticky='E,W', padx=10, pady=5)
        notebook.select(0)

        lf = ttk.LabelFrame(frame, text='Calculation Options')
        r =0
        self._add_labeled_entry('FOV', lf, label='Field of View:',  width=3, value='5', postlabel='arcsec/side', position=(r,0))
        r+=1
        self._add_labeled_entry('detector_oversampling', lf, label='Output Oversampling:',  width=3, value='2', postlabel='x finer than instrument pixels       ', position=(r,0))

        #self.vars['downsamp'] = tk.BooleanVar()
        #self.vars['downsamp'].set(True)
        #self.widgets['downsamp'] = ttk.Checkbutton(lf, text='Save in instr. pixel scale, too?', onvalue=True, offvalue=False,variable=self.vars['downsamp'])
        #self.widgets['downsamp'].grid(row=r, column=4, sticky='E')

        output_options=['Oversampled PSF only', 'Oversampled + Detector Res. PSFs', 'Mock full image from JWST DMS']
        self._add_labeled_dropdown("output_type", fr2, label='Output format:', values=output_options, default=output_options[1], width=31, position=(r,4), sticky='W')


        r+=1
        self._add_labeled_entry('fft_oversampling', lf, label='Coronagraph FFT Oversampling:',  width=3, value='2', postlabel='x finer than Nyquist', position=(r,0))
        r+=1
        self._add_labeled_entry('nlambda', lf, label='# of wavelengths:',  width=3, value='', position=(r,0), postlabel='Leave blank for autoselect')
        r+=1

        self._add_labeled_dropdown("jitter", lf, label='Jitter model:', values=  ['Just use OPDs' ], width=20, position=(r,0), sticky='W', columnspan=2)
        r+=1
        self._add_labeled_dropdown("output_format", lf, label='Output Format:', values=  ['Oversampled image','Detector sampled image','Both as FITS extensions', 'Mock JWST DMS Output' ], width=30, position=(r,0), sticky='W', columnspan=2)
        #self._add_labeled_dropdown("jitter", lf, label='Jitter model:', values=  ['Just use OPDs', 'Gaussian blur', 'Accurate yet SLOW grid'], width=20, position=(r,0), sticky='W', columnspan=2)

        lf.grid(row=4, sticky='E,W', padx=10, pady=5)

        lf = ttk.Frame(frame)

        def addbutton(self,lf, text, command, pos, disabled=False):
            self.widgets[text] = ttk.Button(lf, text=text, command=command )
            self.widgets[text].grid(column=pos, row=0, sticky='E')
            if disabled:
                self.widgets[text].state(['disabled'])

 
        addbutton(self,lf,'Compute PSF', self.ev_calcPSF, 0)
        addbutton(self,lf,'Display PSF', self.ev_displayPSF, 1, disabled=True)
        addbutton(self,lf,'Display profiles', self.ev_displayProfiles, 2, disabled=True)
        addbutton(self,lf,'Save PSF As...', self.ev_SaveAs, 3, disabled=True)
        addbutton(self,lf,'More options...', self.ev_options, 4, disabled=False)

        ttk.Button(lf, text='Quit', command=self.quit).grid(column=5, row=0)
        lf.columnconfigure(2, weight=1)
        lf.columnconfigure(4, weight=1)
        lf.grid(row=5, sticky='E,W', padx=10, pady=15)

        frame.grid(row=0, sticky='N,E,S,W')
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)


    def OnClose(self, event):
        dlg = wx.MessageDialog(self,
            "Do you really want to exit WebbPSF?",
            "Confirm Exit", wx.OK|wx.CANCEL|wx.ICON_QUESTION)
        result = dlg.ShowModal()
        dlg.Destroy()
        if result == wx.ID_OK:
            if self.log_window is not None: self.log_window.Destroy()
            self.Destroy()

    def info(self, messagestring):
        """ Display an informative string in both the log and the window status bar"""
        _log.info(messagestring)
        self.sb.SetStatusText(messagestring)
        self.Refresh()
        self.Update()
        wx.Yield()

    def ev_SaveAs(self, event):
        "Event handler for Save As of output PSFs"
        dlg = wx.FileDialog(self, 'Choose Output Filename to Save PSF', defaultDir = os.getcwd(),
                defaultFile ='PSF_%s_%s.fits' %(self.iname, self.filter), 
                wildcard='*.fits',
                style=wx.SAVE)
        if dlg.ShowModal() == wx.ID_OK:
            path = dlg.GetPath()
            filename = os.path.abspath(path)
            self.PSF_HDUlist.writeto(filename) 
            self.info("Saved to %s" % filename)
        else:
            self.info("User cancelled save.")

    def ev_options(self, event):
        dlg = WebbPSFOptionsDialog(self, input_options = self.advanced_options)
        results = dlg.ShowModal()

        if dlg.results is not None: # none means the user hit 'cancel'
            self.advanced_options = dlg.results

        dlg.Destroy()

    def ev_plotspectrum(self, event):
        "Event handler for Plot Spectrum "
        self._updateFromGUI()
        self.info("Now calculating spectrum model...")

        print "Spectral type is "+self.sptype
        print "Selected instrument tab is "+self.iname
        #if iname != 'TFI':
            #filter = self.widgets[self.iname+"_filter"].get()
        print "Selected instrument filter is "+self.filter


        plt.clf()

        ax1 = plt.subplot(311)
        spectrum = poppy.specFromSpectralType(self.sptype)
        synplot(spectrum)
        ax1.set_ybound(1e-6, 1e8) # hard coded for now
        ax1.yaxis.set_major_locator(matplotlib.ticker.LogLocator(base=1000))
        legend_font = matplotlib.font_manager.FontProperties(size=10)
        ax1.legend(loc='lower right', prop=legend_font)


        ax2 = plt.subplot(312, sharex=ax1)
        ax2.set_ybound(0,1.1)
        #try:
        band = self.inst._getSynphotBandpass(self.inst.filter) #pysynphot.ObsBandpass(obsname)
        band.name = "%s %s" % (self.iname, self.inst.filter)
        synplot(band) #, **kwargs)
        legend_font = matplotlib.font_manager.FontProperties(size=10)
        plt.legend(loc='lower right', prop=legend_font)

        ax2.set_ybound(0,1.1)


        ax3 = plt.subplot(313, sharex=ax1)
        if self.nlambda is None:
            # Automatically determine number of appropriate wavelengths.
            # Make selection based on filter configuration file
            try:
                #if self.inst.name=='TFI':    # filter names are irrelevant for TFI.
                    #nlambda=5
                #else:
                    #filt_width = self.filter[-1]
                    #lookup_table = {'NIRCam': {'2': 10, 'W':20,'M':3,'N':1}, 
                                    #'NIRSpec':{'W':5,'M':3,'N':1}, 
                                    #'MIRI':{'W':5,'M':3,'N':1}, 
                                    #'FGS':{'W':5,'M':3,'N':1}}

                    #nlambda = lookup_table[self.name][filt_width]
                nlambda = self.inst._filter_nlambda_default[self.filter]
            except:
                nlambda=10
        else:
            nlambda = self.nlambda
        ax1.set_xbound(0.1, 100)
        plt.draw()
        waves, weights = self.inst._getWeights(spectrum, nlambda=nlambda)

        wave_step = waves[1]-waves[0]
        plot_waves = np.concatenate( ([waves[0]-wave_step], waves, [waves[-1]+wave_step])) * 1e6
        plot_weights = np.concatenate(([0], weights,[0]))


        plt.ylabel("Weight")
        plt.xlabel("Wavelength [$\mu$m]")

        ax3.plot(plot_waves, plot_weights,  drawstyle='steps-mid')

        ax1.set_xbound(0.1, 100)

        self._refresh_window()
        self.info("Spectrum displayed")

    def _refresh_window(self):
        """ Force the window to refresh, and optionally to show itself if hidden (for recent matplotlibs)"""
        plt.draw()
        from distutils.version import StrictVersion
        if StrictVersion(matplotlib.__version__) >= StrictVersion('1.1'):
            plt.show(block=False)

    def ev_calcPSF(self, event):
        "Event handler for PSF Calculations"
        self._updateFromGUI()
        self.info("Starting PSF calculation...")

        if _HAS_PYSYNPHOT:
            source = poppy.specFromSpectralType(self.sptype)
        else:
            source=None # generic flat spectrum

        self._refresh_window() # pre-display window for calculation updates as it progresses...
        self.PSF_HDUlist = self.inst.calcPSF(source=source, 
                detector_oversample= self.detector_oversampling,
                fft_oversample=self.fft_oversampling,
                fov_arcsec = self.FOV,  nlambda = self.nlambda, display=True)
        #self.PSF_HDUlist.display()
        for w in ['Display PSF', 'Display profiles', 'Save PSF As...']:
           self.widgets[w].Enable(True)
        self._refresh_window()
        self.info("PSF calculation complete")

    def ev_displayPSF(self,event):
        "Event handler for Displaying the PSF"
        #self._updateFromGUI()
        #if self.PSF_HDUlist is not None:
        plt.clf()
        poppy.display_PSF(self.PSF_HDUlist, vmin = self.advanced_options['psf_vmin'], vmax = self.advanced_options['psf_vmax'], 
                scale = self.advanced_options['psf_scale'], cmap= self.advanced_options['psf_cmap'], normalize=self.advanced_options['psf_normalize'])
        self._refresh_window()
        self.info("PSF redisplayed")

    def ev_displayProfiles(self,event):
        "Event handler for Displaying the PSF"
        #self._updateFromGUI()
        poppy.display_profiles(self.PSF_HDUlist)        
        self._refresh_window()
        self.info("Radial profiles displayed.")

    def ev_displayOptics(self,event):
        "Event handler for Displaying the optical system"
        self._updateFromGUI()
        _log.info("Selected OPD is "+str(self.opd_name))

        plt.clf()
        self.inst.display()
        self._refresh_window()
        self.info("Optical system elements displayed.")

    def ev_displayOPD(self,event):
        import poppy.utils

        self._updateFromGUI()
        if self.inst.pupilopd is None:
            tkMessageBox.showwarning( message="You currently have selected no OPD file (i.e. perfect telescope) so there's nothing to display.", title="Can't Display") 
        else:
            if self._enable_opdserver and 'ITM' in self.opd_name:
                opd = self.inst.pupilopd   # will contain the actual OPD loaded in _updateFromGUI just above
            else:
                opd = pyfits.getdata(self.inst.pupilopd[0])     # in this case self.inst.pupilopd is a tuple with a string so we have to load it here. 

            if len(opd.shape) >2:
                opd = opd[self.opd_i,:,:] # grab correct slice

            masked_opd = np.ma.masked_equal(opd,  0) # mask out all pixels which are exactly 0, outside the aperture
            cmap = matplotlib.cm.jet
            cmap.set_bad('k', 0.8)

            plt.clf()
            plt.imshow(masked_opd, cmap=cmap, interpolation='nearest', vmin=-0.5, vmax=0.5)
            poppy.utils.imshow_with_mouseover(masked_opd, cmap=cmap, interpolation='nearest', vmin=-0.5, vmax=0.5)
            plt.title("OPD from %s, #%d" %( os.path.basename(self.opd_name), self.opd_i))
            cb = plt.colorbar(orientation='vertical')
            cb.set_label('microns')

            f = plt.gcf()
            plt.text(0.4, 0.02, "OPD WFE = %6.2f nm RMS" % (masked_opd.std()*1000.), transform=f.transFigure)
        self.info("Optical Path Difference (OPD) now displayed.")

        self._refresh_window()

    def ev_launch_ITM_dialog(self):
        tkMessageBox.showwarning( message="ITM dialog box not yet implemented", title="Can't Display") 

    def ev_update_OPD_labels(self):
        "Update the descriptive text for all OPD files"
        for iname in self.instrument.keys():
            self.ev_update_OPD_label(self.widgets[iname+"_opd"], self.widgets[iname+"_opd_label"], iname)

    def ev_update_OPD_label(self, widget_combobox, widget_label, iname):
        "Update the descriptive text displayed about one OPD file"
        showitm=False # default is do not show
        filename = self.instrument[iname]._datapath +os.sep+ 'OPD'+ os.sep+widget_combobox.get()
        if filename.endswith(".fits"):
            header_summary = pyfits.getheader(filename)['SUMMARY']
            self.widgets[iname+"_opd_i"]['state'] = 'readonly'
        else:  # Special options for non-FITS file inputs
            self.widgets[iname+"_opd_i"]['state'] = 'disabled'
            if 'Zero' in widget_combobox.get():
                header_summary = " 0 nm RMS"
            elif 'ITM' in widget_combobox.get() and self._enable_opdserver:
                header_summary= "Get OPD from ITM Server"
                showitm=True
            elif 'ITM' in widget_combobox.get() and not self._enable_opdserver:
                header_summary = "ITM Server is not running or otherwise unavailable."
            else: # other??
                header_summary = "   "

        widget_label.configure(text=header_summary, width=30)


        if showitm:
            self.widgets[iname+"_itm_coords"].grid() # re-show ITM options
        else:
            self.widgets[iname+"_itm_coords"].grid_remove()  # hide ITM options

    def _updateFromGUI(self):
        """ Update the object's state with all the settings from the GUI
        """
        # get GUI values
        if _HAS_PYSYNPHOT:
            self.sptype = self.widgets['SpType'].GetValue()
        self.iname = self.widgets['tabset'].GetCurrentPage().WebbPSFInstrumentName


        try:
            self.nlambda= int(self.widgets['nlambda'].GetValue())
        except:
            self.nlambda = None # invoke autoselect for nlambda
        self.FOV= float(self.widgets['FOV'].GetValue())
        self.fft_oversampling= int(self.widgets['fft_oversampling'].GetValue())
        self.detector_oversampling= int(self.widgets['detector_oversampling'].GetValue())

        self.output_type = self.widgets['output_format'].GetValue()

        options = {}
        options['rebin'] = not (self.output_type == 'Oversampled PSF only')  #was downsample, which seems wrong?
        options['mock_dms'] = (self.output_type == 'Mock full image from JWST DMS')
        options['jitter'] = self.widgets['jitter'].GetValue()

        # and get the values that may have previously been set by the 'advanced options' dialog
        if self.advanced_options is not None:
            for a in self.advanced_options.keys():
                options[a] = self.advanced_options[a]


        # configure the relevant instrument object
        self.inst = self.instrument[self.iname]
        self.filter = self.widgets[self.iname+"_filter"].GetValue() # save for use in default filenames, etc.
        self.inst.filter = self.filter
        _log.info("Selected filter: "+self.filter)

        self.opd_name = self.widgets[self.iname+"_opd"].GetValue()
        if self._enable_opdserver and 'ITM' in self.opd_name:
            # get from ITM server
            self.opd_i= 0
            self.inst.pupilopd = self._opdserver.get_OPD(return_as="FITS")
            self.opd_name = "OPD from ITM OPD GUI"

        elif self.opd_name == "Zero OPD (perfect)": 
            # perfect OPD
            self.opd_name = "Perfect"
            self.inst.pupilopd = None
        else:
            # Regular FITS file version
            self.opd_name= self.widgets[self.iname+"_opd"].GetValue()
            self.opd_i= int(self.widgets[self.iname+"_opd_i"].GetValue())
            self.inst.pupilopd = (self.inst._datapath+os.sep+"OPD"+os.sep+self.opd_name,self.opd_i)  #filename, slice

        _log.info("Selected OPD is "+str(self.opd_name))


        if self.iname+"_coron" in self.widgets:
            self.inst.image_mask = self.widgets[self.iname+"_coron"].GetValue()
            self.inst.pupil_mask = self.widgets[self.iname+"_pupil"].GetValue()
            # TODO read in mis-registration options here.


            options['source_offset_r'] = float(self.widgets["source_off_r"].GetValue())
            options['source_offset_theta'] = float(self.widgets["source_off_theta"].GetValue())
            options['pupil_shift_x'] = float(self.widgets[self.iname+"_pupilshift_x"].GetValue())/100. # convert from percent to fraction
            options['pupil_shift_y'] = float(self.widgets[self.iname+"_pupilshift_y"].GetValue())/100. # convert from percent to fraction

        self.inst.options = options


#-------------------------------------------------------------------------

class WebbPSFMenuBar(wx.MenuBar):
    def __init__(self,parent):
        wx.MenuBar.__init__(self)
        item_keys =['save_psf','save_profile', 'doc']

        self.ids = {}
        for key in item_keys:
            self.ids[key]=wx.NewId()


        filemenu = wx.Menu()
        self.SavePSF = filemenu.Append(self.ids['save_psf'], '&Save PSF as...\tCtrl+Shift+S')
        self.SaveProfile =filemenu.Append(self.ids['save_profile'], 'Save profile data as...\tCtrl+Shift+S')
        #filemenu.AppendSeparator()
        self.Exit = filemenu.Append(wx.ID_EXIT, 'E&xit', 'Exit this program')

        # these start out disabled since no PSF calculated yet:
        self.SavePSF.Enable(False)
        self.SaveProfile.Enable(False)

        helpmenu = wx.Menu()
        self.Docs = helpmenu.Append(self.ids['doc'], 'WebbPSF Documentation\tCtrl+d')
        self.About = helpmenu.Append(wx.ID_ABOUT, '&About WebbPSF', 'About this program')

        self.Append(filemenu, '&File')
        self.Append(helpmenu, '&Help')



class WebbPSFOptionsDialog(wx.Dialog):
    """ Dialog box for WebbPSF options 

    TODO: investigate wx.Validator to validate the text input fields
    """
    def __init__(self, parent=None, id=-1, title="WebbPSF Options", 
            input_options={'force_coron': False, 'no_sam': False, 'parity':2,
                'psf_scale':'log', 'psf_normalize':'Peak', 'psf_cmap_str': 'Jet (blue to red)',
                'psf_vmin':1e-8, 'psf_vmax':1.0 }): 
        wx.Dialog.__init__(self,parent,id=id,title=title)

        self.parent=parent
        self.input_options = input_options

        self.results = None # in case we cancel this gets returned
        self.widgets = {}
        self.values = {}

        colortables = [
         ('Jet (blue to red)',matplotlib.cm.jet),
         ('Gray', matplotlib.cm.gray),
         ('Heat (black-red-yellow)', matplotlib.cm.gist_heat),
         ('Copper (black to tan)',matplotlib.cm.copper),
         ('Stern',matplotlib.cm.gist_stern),
         ('Prism (repeating rainbow)', matplotlib.cm.prism)]

        try:
            import collections
            self.colortables = collections.OrderedDict(colortables)
        except:
            self.colortables = dict(colortables)

        self.values['force_coron'] = ['regular propagation (MFT)', 'full coronagraphic propagation (FFT/SAM)']
        self.values['no_sam'] = ['semi-analytic method if possible', 'basic FFT method always']


        self._createWidgets()
 
    def _add_labeled_dropdown(self, name, parent, parentsizer, label="Entry:", choices=None, default=0, width=5, position=(0,0), columnspan=1, **kwargs):
        """convenient wrapper for adding a Combobox

        columnspan sets the span for the combobox itself
        """

        mylabel = wx.StaticText(parent, -1,label=label)
        parentsizer.Add( mylabel, position,  (1,1), wx.EXPAND)

        if choices is None:
            try:
                choices = self.values[name]
            except:
                choices = ['Option A','Option B']

        if isinstance(default,int):
            value = choices[default]
        else:
            value=default

        mycombo = wx.ComboBox(parent, -1,value=value, choices=choices, style=wx.CB_DROPDOWN|wx.CB_READONLY)
        parentsizer.Add( mycombo, (position[0],position[1]+1),  (1,columnspan), wx.EXPAND)

        self.widgets[name] = mycombo
 

    def _add_labeled_entry(self, name, parent, parentsizer, label="Entry:", value=None, format="%.2g", 
            width=5, position=(0,0), postlabel=None, **kwargs):
        "convenient wrapper for adding an Entry"
        mylabel = wx.StaticText(parent, -1,label=label)
        parentsizer.Add( mylabel, position,  (1,1), wx.EXPAND)


        if value is None:
            try:
                value=format % self.input_options[name]
            except:
                value=""

        mytext = wx.TextCtrl(parent, -1,value=value)
        parentsizer.Add( mytext, (position[0],position[1]+1),  (1,1), wx.EXPAND)

        self.widgets[name] = mytext

        if postlabel is not None:
            mylabel2 = wx.StaticText(parent, -1,label=postlabel)
            parentsizer.Add( mylabel2, (position[0],position[1]+2),  (1,1), wx.EXPAND)



    def _createWidgets(self):

        topSizer = wx.BoxSizer(wx.VERTICAL)

        topPanel = wx.Panel(self)
        topPanelSizer = wx.FlexGridSizer(rows=3,cols=1, hgap=5, vgap=10)
        #topPanelSizer = wx.BoxSizer(wx.VERTICAL)

        panel1 = wx.Panel(topPanel, style=wx.SIMPLE_BORDER|wx.EXPAND)
        sizer = wx.GridBagSizer()

        txt = wx.StaticText(panel1,-1,label="Propagation Calculation Options")
        sizer.Add(txt,(0,0),(1,3),wx.EXPAND|wx.ALIGN_CENTER_HORIZONTAL)


        r=2
        self._add_labeled_dropdown("force_coron", panel1,sizer, 
                label='    Direct imaging calculations use: ', 
                default = 1 if self.input_options['force_coron'] else 0, position=(r,0))

        r+=1
        self._add_labeled_dropdown("no_sam", panel1,sizer, 
                label='    Coronagraphic calculations use', 
                default= 1 if self.input_options['no_sam'] else 0, position=(r,0))
        r+=1
        self._add_labeled_dropdown("parity", panel1,sizer, 
                label='    Output pixel grid parity is', 
                choices=['odd', 'even', 'either'], default=self.input_options['parity'], position=(r,0))

        #sizer.AddGrowableCol(0)
        panel1.SetSizerAndFit(sizer)

        panel2 = wx.Panel(topPanel, style=wx.SIMPLE_BORDER|wx.EXPAND)
        sizer = wx.GridBagSizer()

        r=0
        txt = wx.StaticText(panel2,-1,label="PSF Display Options")
        sizer.Add(txt,(r,0),(1,3),wx.EXPAND|wx.ALIGN_CENTER_HORIZONTAL)


        r+=2
        self._add_labeled_dropdown("psf_scale", panel2,sizer, label='    Display scale:', choices=['log','linear'],
                default=self.input_options['psf_scale'], position=(r,0))

        r+=1
        self._add_labeled_entry("psf_vmin", panel2,sizer, label='    Min scale value:', 
            format="%.2g", width=7, 
            position=(r,0))
        r+=1
        self._add_labeled_entry("psf_vmax", panel2,sizer, label='    Max scale value:', 
            format="%.2g", width=7, 
            position=(r,0))
        r+=1
        self._add_labeled_dropdown("psf_normalize", panel2,sizer,
                label='    Normalize PSF to:', choices=['Total', 'Peak'], 
                default=self.input_options['psf_normalize'], position=(r,0))
        r+=1
        self._add_labeled_dropdown("psf_cmap", panel2,sizer, label='    Color table:', 
                choices=[a for a in self.colortables.keys()],  
                default=self.input_options['psf_cmap_str'], 
                position=(r,0))
        panel2.SetSizerAndFit(sizer)


        bbar = self.CreateStdDialogButtonSizer( wx.OK | wx.CANCEL)
        self.Bind(wx.EVT_BUTTON, self.OnButtonOK, id=wx.ID_OK)
        #self.Bind(wx.EVT_BUTTON, self.OnButtonCancel, id=wx.ID_CANCEL)
 

        topPanelSizer.Add(panel1, 1,wx.EXPAND)
        topPanelSizer.Add(panel2, 1, wx.EXPAND)
        #topPanelSizer.Add(panel3,1, wx.EXPAND)
        topPanelSizer.Add(bbar,1, wx.EXPAND)
        #topPanel.AddGrowableCol(0)
        topPanel.SetSizerAndFit(topPanelSizer)
 
        topSizer.Add(topPanel, 1, flag=wx.EXPAND|wx.ALL, border=10)
        self.SetSizerAndFit(topSizer)
        self.Show(True)
    #def OnButtonCancel(self, event):
        #print "User pressed Cancel"
        #self.Close()
        #self.Destroy()

    def OnButtonOK(self, event):
        print "User pressed OK"
        try:
            results = {}
            results['force_coron'] = self.widgets['force_coron'].GetValue() == 'full coronagraphic propagation (FFT/SAM)'
            results['no_sam'] = self.widgets['no_sam'].GetValue() == 'basic FFT method always'
            results['parity'] = self.widgets['parity'].GetValue() 
            results['psf_scale'] = self.widgets['psf_scale'].GetValue() 
            results['psf_vmax'] = float(self.widgets['psf_vmax'].GetValue())
            results['psf_vmin'] = float(self.widgets['psf_vmin'].GetValue())
            results['psf_cmap_str'] = self.widgets['psf_cmap'].GetValue()
            results['psf_cmap'] = self.colortables[self.widgets['psf_cmap'].GetValue() ]
            results['psf_normalize'] = self.widgets['psf_normalize'].GetValue()


            print results
            self.results = results # for access from calling routine

            self.Close()
            #self.Destroy() # return... If called as a modal dialog, should ShowModal and Destroy from calling routine?
        except:
            _log.error("Invalid entries in one or more fields. Please check values and re-enter!")


#-------------------------------------------------------------------------
#
# Classes for displaying log messages in a separate window

class WxLog(logging.Handler):
    def __init__(self, ctrl):
        logging.Handler.__init__(self)
        self.ctrl = ctrl
    def emit(self, record):
        self.ctrl.AppendText(self.format(record)+"\n")
        self.ctrl.Update()

class LogFrame(wx.Frame):
    def __init__(self, parent=None, id=-1, pos=None, size=(600,300)):
        wx.Frame.__init__(self, parent, id=id, title="logging test", size=size,pos=pos)
        #self.level = 4
        log = wx.TextCtrl(self, style=wx.TE_MULTILINE)
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(log, 1, wx.EXPAND)
        self.SetSizer(sizer)


        hdlr = WxLog(log)
        hdlr.setFormatter(logging.Formatter('%(name)-8s %(levelname)-8s: %(message)s'))

        logging.getLogger('webbpsf').addHandler(hdlr)
        logging.getLogger('poppy').addHandler(hdlr)
        

#-------------------------------------------------------------------------

class HtmlWindow(wx.html.HtmlWindow):
    def __init__(self, parent, id, size=(600,400)):
        wx.html.HtmlWindow.__init__(self,parent, id, size=size)
        if "gtk2" in wx.PlatformInfo:
            self.SetStandardFonts()

    def OnLinkClicked(self, link):
        wx.LaunchDefaultBrowser(link.GetHref())

class AboutBox(wx.Dialog):
    def __init__(self):
        wx.Dialog.__init__(self, None, wx.ID_ANY, "About WebbPSF",
            style=wx.DEFAULT_DIALOG_STYLE|wx.THICK_FRAME|wx.RESIZE_BORDER|
                wx.TAB_TRAVERSAL)


        aboutText = """<p>This is the <b>WebbPSF Point Spread Function Simulator</b> for the James Webb Space Telescope (JWST),
version %(webbpsf)s
<p>
<center>
See <a href="http://www.stsci.edu/jwst/software/webbpsf">the WebbPSF home page</a>
</center>
<p>
(c) 2010-2012 by Marshall Perrin, <a href="mailto:mperrin@stsci.edu">mperrin@stsci.edu</a>.
<br>
With contributions from: Anand Sivaramakrishnan, Remi Soummer, &amp; Klaus Pontoppidan
<p>
WebbPSF is running with the following software versions:
<ul>
<li><b>Python</b>: %(python)s 
<li><b>numpy</b>: %(numpy)s
<li><b>matplotlib</b>: %(matplotlib)s
<li><b>pyfits</b>: %(pyfits)s
<li><b>atpy</b>: %(atpy)s
<li><b>wxPython</b>: %(wxpy)s  
</ul>
</p>"""

        import sys, pyfits
        hwin = HtmlWindow(self, wx.ID_ANY, size=(400,200))
        vers = {}
        try:
            #importing webbpsf from another directory?
            vers["webbpsf"] = webbpsf_core.__version__
        except:
            #importing from within webbpsf source directory
            import _version
            vers["webbpsf"] = _version.__version__
        vers["python"] = sys.version.split()[0]
        vers["wxpy"] = wx.VERSION_STRING
        vers['numpy'] = np.__version__
        vers['matplotlib'] = matplotlib.__version__
        #vers['atpy'] = atpy.__version__
        vers['pyfits'] = pyfits.__version__
        hwin.SetPage(aboutText % vers)
        btn = hwin.FindWindowById(wx.ID_OK)
        irep = hwin.GetInternalRepresentation()
        hwin.SetSize((irep.GetWidth()+25, irep.GetHeight()+10))
        self.SetClientSize(hwin.GetSize())
        self.CentreOnParent(wx.BOTH)
        self.SetFocus()


#-------------------------------------------------------------------------

def synplot(thing, waveunit='micron', label=None, **kwargs):
    """ Plot a single PySynPhot object (either SpectralElement or SourceSpectrum)
    versus wavelength, with nice axes labels.

    Really just a simple convenience function.
    """

    # convert to requested display unit.
    wave = thing.waveunits.Convert(thing.wave,waveunit)


    if label is None:
        label = thing.name


    if isinstance(thing, pysynphot.spectrum.SourceSpectrum):
        artist = plt.loglog(wave, thing.flux, label=label, **kwargs)
        plt.xlabel("Wavelength [%s]" % waveunit)
        if str(thing.fluxunits) == 'flam':
            plt.ylabel("Flux [%s]" % ' erg cm$^{-2}$ s$^{-1}$ Ang$^{-1}$' )
        else:
            plt.ylabel("Flux [%s]" % thing.fluxunits)
    elif isinstance(thing, pysynphot.spectrum.SpectralElement):
        artist = plt.plot(wave, thing.throughput,label=label, **kwargs)
        plt.xlabel("Wavelength [%s]" % waveunit)
        plt.ylabel("Throughput")
        plt.gca().set_ylim(0,1)
    else:
        _log.error( "Don't know how to plot that object...")
        artist = None
    return artist




def wxgui(fignum=1, showlog=True):
    # enable log message printout
    logging.basicConfig(level=logging.INFO,format='%(name)-10s: %(levelname)-8s %(message)s')
    # start the GUI

    app = wx.App()
    gui = WebbPSF_GUI()
    gui.Show()

    if showlog: 
        # start it immediately below the main window
        gpos = gui.GetScreenPosition()
        gsize = gui.GetSize()

        logwin = LogFrame(pos=(gpos[0], gpos[1]+gsize[1]), size=(gsize[0], 200))
        logwin.Show()

        gui.log_window = logwin
    #bout = AboutBox()
    #about.ShowModal()
    #gui = WebbPSFOptionsDialog()
    plt.figure(fignum)
    #plt.show(block=False)
    app.MainLoop()



if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,format='%(name)-10s: %(levelname)-8s %(message)s')
    wxgui()


