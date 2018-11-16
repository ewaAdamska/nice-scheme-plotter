#!/usr/bin/env python

###############
#Update:
#2/12/2015:
# correct the scientific output: digits after decimal point
#3/18/2015:
#    add codes in "decode_value" to read level like "1234.5+X(12)" for excel2ensdf
#05/06/2015:
#    add codes in "format_uncertainty" to handle real-value string like, "3.1 0.123"
#                                                                         "0.7 0.07"
#01/06/2016:
#    add codes in "decode_value" to read level like "X+1234.5(12)" for excel2ensdf
#    add code in "read_header" to read settings, like comment data in new line, comment
#        data name translation
#12/28/2016:
#    revise "delay_record_names" by removing "EDP","EDN","EDA" and using "EP" instead
#    add comment and document record names for delayed-particle records
#07/06/2017:
#    revise "format_ENSDF" to remove trailing zeros in the input value_str if unc_str 
#      is non-numerical
#    add "format_ENSDF0(value_str,unc_str,unc_ndigits" to force formating the 
#      input strings into ENSDF format with uncertainty digits=unc_nidigts
#07/10/2017:
#    revise "format_ENSDF" to correctly round up at last '5. Python rounds down at the
#    last '5', eg, 24.5 to 24 not 25, but 24.50000001 to 25. Fix: value *(1+1.0E-9) 
#07/11/2017:
#    revise "V_operation" to correctly round decimal digits for cases without uncertainties
#07/18/2017:
#    add functions: getZA(), readLines
#07/19/2017:
#    improve sorting algorithm in sort_gammas(), sort_levels(), much faster now
#07/21/2017:
#    add more ICC fields
#07/22/2017:
#    add translateNucleus() and translateDSID() functions
#07/23/2017:
#    add Average class and improve average functions

   
from xlrd import open_workbook,XL_CELL_TEXT 

import os, math, string, sys, os.path, re


# DO NOT MODIFY THE DICTIONARY FOR FIELD NAMES AND POSITIONS IN ENSDF FILE#
# each element has format: field name:(pos,width), -1 is used if not applicable  
# 'pos' starts from 1 not 0 
el_field_name='EL'
del_field_name='DEL'

eg_field_name='EG'
deg_field_name='DEG'

all_record_names=[] # fixed ENSDF records of all types (with fixed positions in ENSDF line)

all_fields={}  #=all_records+all others in continuation line

level_record_names   = ['EL','DEL','JPI','T','DT','TU','L','S','DS','LFLAG','MS','LQUE']
beta_record_names    = ['EB','DEB','IB','DIB','LOGFT','DLOGFT','UN','DFLAG','DQUE']
ec_record_names      = ['EB','DEB','IBE','DIBE','IE','DIE','LOGFT','DLOGFT','TIE','DTIE','UN','DFLAG','DQUE']
alpha_record_names   = ['EA','DEA','IA','DIA','HF','DHF','DFLAG','DQUE']
gamma_record_names   = ['EG','DEG','RI','DRI','MUL','MR','DMR','CC','DCC','TI','DTI','GFLAG','GCOIN','GQUE']
delay_record_names   = ['EP','DEP','IP','DIP','ED','WIDTH','DWIDTH','LP',
                        'PFLAG','PCOIN','PQUE']

level_comment_names =['CL','CA','CE','CB','CDP','CDN','CDA','CD','DL','DA','DE','DB','DDP','DDN','DDA','DD'
                      'SL','SA','SE','SB']
gamma_comment_names =['CG','DG','SG']

all_record_names.extend(level_record_names)
all_record_names.extend(gamma_record_names)
all_record_names.extend(ec_record_names)
all_record_names.extend(alpha_record_names)
all_record_names.extend(beta_record_names)


parent_record_names= ['PID','EP','DEP','JPA','TP','DTP','TPU','QP','DQP']
norm_record_names  = ['NR','DNR','NT','DNT','BR','DBR','NB','DNB','NP','DNP']
pn_record_names    = ['NRBR','DNRBR','NTBR','DNTBR','NBBR','DNBBR','NP','DNP','PNCOM','PNOPT']
Q_record_names     = ['Q','DQ','SN','DSN','SP','DSP','QA','DQA','QREF']

#format: 'field_name':(col#,length)
level_fields  =    {'EL':(10,10),'DEL':(20,2),'JPI':(22,18),'T':(40,10),'DT':(50,6),'TU':(-1,-1),'L':(56,9),
                    'S':(65,10),'DS':(75,2),
                    'MS':(78,2), #mark for meta-stable state
                    'EB':(10,10),'DEB':(20,2),'IB':(22,8),'DIB':(30,2),
                    'IBE':(22,8),'DIBE':(30,2), #B+ decay branch
                    'LOGFT':(42,8),'DLOGFT':(50,6),
                    'UN':(78,2),#forbiddenness, e.g., '1U','2U'
                    'IE':(32,8),'DIE':(40,2), # EC decay branch
                    'TIE':(65,10),'DTIE':(75,2),# EC+B+ total decay intensity
                    'ISPIN':(-1,-1),
                    'GF':(-1,-1),'DGF':(-1,-1), #g-factor
                    'EA':(10,10),'DEA':(20,2),'IA':(22,8),'DIA':(30,2),'HF':(32,8),'DHF':(40,2),
                    'EP':(10,10),'DEP':(20,2),'IP':(22,8),'DIP':(30,2),'ED':(32,8), #delayed-particle
                    'EDP':(10,10),'DEDP':(20,2),'EDN':(10,10),'DEDN':(20,2),'EDA':(10,10),'DEDA':(20,2),#used by xls2ens for delayed
                    'WIDTH':(40,10),'DWIDTH':(50,6),'LP':(56,9),
                    'LFLAG':(77,-1), #level flags
                    'DFLAG':(77,-1), #decay flags B+, B- and EC, ALPHA
                    #'AFLAG':(77,-1), #flags for alpha decy
                    'PFLAG':(77,-1), 'PCOIN':(78,-1),#particle flags and coin
                    'BAND':(77,-1), 'SEQ':(77,-1),#band and sequence flags
                    'CL':(-1,-1),'DL':(-1,-1),'SL':(-1,-1),   # general level comment and level document record
                    'CB':(-1,-1),'CE':(-1,-1),'CA':(-1,-1), #coments for B+/-, EC and alpha decays
                    'CD':(-1,-1),'DD':(-1,-1),                              #comments and documents for delayed-particle
                    'CDN':(-1,-1),'DDN':(-1,-1),
                    'CDP':(-1,-1),'DDP':(-1,-1),
                    'CDA':(-1,-1),'DDA':(-1,-1),
                    'DB':(-1,-1),'DE':(-1,-1),'DA':(-1,-1), #documents for B+/-, EC and alpha decays
                    'SB':(-1,-1),'SE':(-1,-1),'SA':(-1,-1), #calculated lines
                    'LQUE':(80,-1),'DQUE':(80,-1),'PQUE':(80,-1), #question marks for level, decay and delayed-particle records 
                    'LCD1':(-1,-1),'DLCD1':(-1,-1),'LCD2':(-1,-1),'DLCD2':(-1,-1),
                    'LCD3':(-1,-1),'DLCD3':(-1,-1), #for data to be put in comment records starting with '$'
                    'DCD1':(-1,-1),'DDCD1':(-1,-1),'DCD2':(-1,-1),'DDCD2':(-1,-1),
                    'DCD3':(-1,-1),'DDCD3':(-1,-1), #for data to be put in decay comment records starting with '$'      
                    'PCD1':(-1,-1),'DPCD1':(-1,-1),'PCD2':(-1,-1),'DPCD2':(-1,-1),
                    'PCD3':(-1,-1),'DPCD3':(-1,-1), #for data to be put in delay comment records starting with '$'      
                    'LUDN':(-1,-1),'LUDD':(-1,-1),'DLUDD':(-1,-1),'LUDU':(-1,-1),#user-defined record name, data value, uncertainty, unit               
                    'LUDN1':(-1,-1),'LUDD1':(-1,-1),'DLUDD1':(-1,-1),'LUDU1':(-1,-1),#user-defined record name, data value, uncertainty, unit               
                    'LUDN2':(-1,-1),'LUDD2':(-1,-1),'DLUDD2':(-1,-1),'LUDU2':(-1,-1),#user-defined record name, data value, uncertainty, unit               
                    'XREF':(-1,-1),'MOMM1':(-1,-1),'MOMM2':(-1,-1),'MOMM3':(-1,-1),
                    'MOME1':(-1,-1),'MOME2':(-1,-1),'MOME3':(-1,-1)
                    }


level_EM  =        {'BE1UP':(-1,-1),'DBE1UP':(-1,-1),'BE2UP':(-1,-1),'DBE2UP':(-1,-1),'BE3UP':(-1,-1),'DBE3UP':(-1,-1),
                    'BE4UP':(-1,-1),'DBE4UP':(-1,-1),'BE5UP':(-1,-1),'DBE5UP':(-1,-1),
                    'BM1UP':(-1,-1),'DBM1UP':(-1,-1),'BM2UP':(-1,-1),'DBM2UP':(-1,-1),'BM3UP':(-1,-1),'DBM3UP':(-1,-1),
                    'BM4UP':(-1,-1),'DBM4UP':(-1,-1),'BM5UP':(-1,-1),'DBM5UP':(-1,-1),
                    'BE1WUP':(-1,-1),'DBE1WUP':(-1,-1),'BE2WUP':(-1,-1),'DBE2WUP':(-1,-1),'BE3WUP':(-1,-1),'DBE3WUP':(-1,-1),
                    'DBE4WUP':(-1,-1),'DBE4WUP':(-1,-1),'BE5WUP':(-1,-1),'DBE5WUP':(-1,-1),
                    'BM1WUP':(-1,-1),'DBM1WUP':(-1,-1),'BM2WUP':(-1,-1),'DBM2WUP':(-1,-1),'BM3WUP':(-1,-1),'DBM3WUP':(-1,-1),
                    'DBM4WUP':(-1,-1),'DBM4WUP':(-1,-1),'BM5WUP':(-1,-1),'DBM5WUP':(-1,-1)
                   }
level_MOM =        {'MOMM1':(-1,-1),'DMOMM1':(-1,-1),'MOMM2':(-1,-1),'DMOMM2':(-1,-1),'MOMM3':(-1,-1),'DMOMM3':(-1,-1),
                    'MOME1':(-1,-1),'DMOME1':(-1,-1),'MOME2':(-1,-1),'DMOME2':(-1,-1),'MOME3':(-1,-1),'DMOME3':(-1,-1)
                   }
level_fields.update(level_EM)
level_fields.update(level_MOM)

gamma_fields  =    {'EG':(10,10),'DEG':(20,2),'RI':(22,8),'DRI':(30,2),'MUL':(32,10),'MR':(42,8),'DMR':(50,6),
                    'A2':(-1,-1),'DA2':(-1,-1),'A4':(-1,-1),'DA4':(-1,-1),'A6':(-1,-1),'DA6':(-1,-1),
                    'CG':(-1,-1), 'DG':(-1,-1),'SG':(-1,-1),#general gamma comment and gamma document record
                    'TI':(65,10),'DTI':(75,2),
                    'CC':(56,7),'DCC':(63,2),
                    'DCO':(-1,-1),'DDCO':(-1,-1),'POL':(-1,-1),'DPOL':(-1,-1),
                    'GFLAG':(77,-1),'GCOIN':(78,-1),'GQUE':(80,-1),'FL':(-1,-1),
                    'GCD1':(-1,-1),'DGCD1':(-1,-1),'GCD2':(-1,-1),'DGCD2':(-1,-1),
                    'GCD3':(-1,-1),'DGCD3':(-1,-1),  #for data to be put in comment records starting with '$'
                    'GUDN':(-1,-1),'GUDD':(-1,-1),'DGUDD':(-1,-1),'GUDU':(-1,-1),#user-defined record name, data value, uncertainty, unit               
                    'GUDN1':(-1,-1),'GUDD1':(-1,-1),'DGUDD1':(-1,-1),'GUDU1':(-1,-1),#user-defined record name, data value, uncertainty, unit               
                    'GUDN2':(-1,-1),'GUDD2':(-1,-1),'DGUDD2':(-1,-1),'GUDU2':(-1,-1),#user-defined record name, data value, uncertainty, unit               
                    'EF':(-1,-1),'DEF':(-1,-1),'JF':(-1,-1),'EI':(-1,-1),'DEI':(-1,-1),'JI':(-1,-1) #for final and initial levels of gamma
                    }
gamma_EM =         {'BE1':(-1,-1),'DBE1':(-1,-1),'BE2':(-1,-1),'DBE2':(-1,-1),'BE3':(-1,-1),'DBE3':(-1,-1),
                    'BE4':(-1,-1),'DBE4':(-1,-1),'BE5':(-1,-1),'DBE5':(-1,-1),
                    'BM1':(-1,-1),'DBM1':(-1,-1),'BM2':(-1,-1),'DBM2':(-1,-1),'BM3':(-1,-1),'DBM3':(-1,-1),
                    'BM4':(-1,-1),'DBM4':(-1,-1),'BM5':(-1,-1),'DBM5':(-1,-1),
                    'BE1W':(-1,-1),'DBE1W':(-1,-1),'BE2W':(-1,-1),'DBE2W':(-1,-1),'BE3W':(-1,-1),'DBE3W':(-1,-1),
                    'BE4W':(-1,-1),'DBE4W':(-1,-1),'BE5W':(-1,-1),'DBE5W':(-1,-1),
                    'BM1W':(-1,-1),'DBM1W':(-1,-1),'BM2W':(-1,-1),'DBM2W':(-1,-1),'BM3W':(-1,-1),'DBM3W':(-1,-1),
                    'DBM4W':(-1,-1),'DBM4W':(-1,-1),'BM5W':(-1,-1),'DBM5W':(-1,-1)
                   }



ICC_fields    =    {'ECC':(-1,-1),'DECC':(-1,-1),'EKC':(-1,-1),'DEKC':(-1,-1),'ELC':(-1,-1),'DELC':(-1,-1),
                    'EMC':(-1,-1),'DEMC':(-1,-1),'ENC':(-1,-1),'DENC':(-1,-1),
                    'EL1C':(-1,-1),'DEL1C':(-1,-1),'EL2C':(-1,-1),'DEL2C':(-1,-1),'EL3C':(-1,-1),'DEL3C':(-1,-1),
                    'EL12C':(-1,-1),'DEL12C':(-1,-1),'EL23C':(-1,-1),'DEL23C':(-1,-1),'ELC+':(-1,-1),'DELC+':(-1,-1),
                    'EM1C':(-1,-1),'DEM1C':(-1,-1),'EM2C':(-1,-1),'DEM2C':(-1,-1),'EM3C':(-1,-1),'DEM3C':(-1,-1),
                    'EM4C':(-1,-1),'DM4C':(-1,-1),'EM5C':(-1,-1),'DEM5C':(-1,-1),'EMC+':(-1,-1),'DEMC+':(-1,-1),
                    'EN1C':(-1,-1),'DEN1C':(-1,-1),'EN2C':(-1,-1),'DEN2C':(-1,-1),'EN3C':(-1,-1),'DEN3C':(-1,-1),
                    'EN4C':(-1,-1),'DN4C':(-1,-1),'EN23C':(-1,-1),'DEN23C':(-1,-1),'ENC+':(-1,-1),'DENC+':(-1,-1)
                   }

gamma_fields.update(gamma_EM)
gamma_fields.update(ICC_fields)

#parent record fields for decay dataset
parent_fields =    {'PID':(1,5),'EP':(10,10),'DEP':(20,2),'JPA':(22,18),'TP':(40,10),'DTP':(50,6),'TPU':(-1,-1),           
                    'QP':(65,10),'DQP':(75,2),
                    'CP':(-1,-1),   # general parent comment    
                    'PDOC':(-1,-1)   #document comment      
                   }

#N record fields
norm_fields   =    {'NR':(10,10),'DNR':(20,2),'NT':(22,8),'DNT':(30,2),'BR':(32,8),'DBR':(40,2),
                    'NB':(42,8),'DNB':(50,6),'NP':(56,7),'DNP':(63,2),
                    'CN':(-1,-1),'NDOC':(-1,-1)
                   }

#PN record fields
pn_fields     =    {'NRBR':(10,10),'DNRBR':(20,2),'NTBR':(22,8),'DNTBR':(30,2),
                    'NBBR':(42,8),'DNBBR':(50,6),'NP':(56,7),'DNP':(63,2),'PNCOM':(77,1),'PNOPT':(78,1),
                    'CPN':(-1,-1),'PNDOC':(-1,-1)
                   }
#Q-value record fields
Q_fields      =    {'Q':(10,10),'DQ':(20,2),'SN':(22,8),'DSN':(30,2),'SP':(32,8),'DSP':(40,2),
                    'QA':(42,8),'DQA':(50,6),'QREF':(56,25),
                    'CQ':(-1,-1),'QDOC':(-1,-1)
                   }

all_fields.update(level_fields)
all_fields.update(gamma_fields)

#level_field_names=(c for c in level_fields) #generator
#gamma_field_names=(c for c in gamma_fields) #generator

#The resulting lists don't have the same order as in the dictionaries
#sort() will sort the list according original order?
level_field_names=level_fields.keys()
gamma_field_names=gamma_fields.keys()
all_field_names=all_fields.keys()

parent_field_names=parent_fields.keys()
norm_field_names  =norm_fields.keys()
pn_field_names    =pn_fields.keys()
Q_field_names     =Q_fields.keys()

letters=set('abcdefghijklmnopqrstuvwxyz')
digits=set('0123456789')
operators=['<', '<=','>', '>=', '~','=']
ENSDF_op =['LT','LE','GT','GE','AP',' ']
ENSDF_op_lower=['<','|<','>','|>','~',' ']
pm_op=['+','-']
math_op_name=['ADD','SUBTRACT','MULTIPLY','DIVIDE','INVERSE']
text_op_name=['APPEND','PREFIX','REPLACE']

#NOTE:calculated lines marked by 'S' will be treated separately
continuation_marks=['1','2','3','4','5','6','7','8','9','B','F','X','M','S']

#record type: col6-8
fixed_record_types=['  L','  G','  B','  E','  A','  D']

comment_buffer=[]

prefix_general_com =' C  '
prefix_level       ='  L '
prefix_gamma       ='  G '
prefix_level_con   ='2 L '
prefix_gamma_con   ='2 G '
prefix_level_com   =' CL '
prefix_gamma_com   =' CG '
prefix_level_doc   =' DL '
prefix_gamma_doc   =' DG '
prefix_level_EM    ='2 L '
prefix_gamma_EM    ='2 G '
prefix_level_FLAG  ='F L '
prefix_gamma_FLAG  ='F G '
prefix_level_xref  ='X L '
prefix_level_MOM   ='2 L '
prefix_decay_con   ='2 B '
prefix_decay_com   =' CB '#for beta decay by defulat, modify the prefix for other decays
prefix_delay_com   =' CDP'#for delayed-proton by default
prefix_delay_con   ='2 DP'

prefix_parent      ='  P '
prefix_norm        ='  N '
prefix_pn          =' PN '
prefix_Q           ='  Q '

prefix_parent_com  =' CP '
prefix_norm_com    =' CN '
prefix_pn_com      ='2PN '
prefix_Q_com       =' CQ '

prefix_parent_doc  =' DP '
prefix_norm_doc    =' DN '
prefix_pn_doc      ='DPN '
prefix_Q_doc       =' DQ '

prefix_history     ='  H '
prefix_xref        ='  X'

prefix={'general_com':prefix_general_com,
          'level'      :prefix_level,       
          'gamma'      :prefix_gamma,       
          'level_con'  :prefix_level_con,   
          'gamma_con'  :prefix_gamma_con,   
          'level_com'  :prefix_level_com,   
          'gamma_com'  :prefix_gamma_com,   
          'level_doc'  :prefix_level_doc,   
          'gamma_doc'  :prefix_gamma_doc,   
          'level_EM'   :prefix_level_EM,    
          'gamma_EM'   :prefix_gamma_EM,    
          'level_FLAG' :prefix_level_FLAG,  
          'gamma_FLAG' :prefix_gamma_FLAG,  
          'level_xref' :prefix_level_xref,  
          'level_MOM'  :prefix_level_MOM, 
          'decay_con'  :prefix_decay_con,
          'decay_com'  :prefix_decay_com,   

          'delay_con'  :prefix_delay_con,
          'delay_com'  :prefix_delay_com,              
                                      
          'parent'     :prefix_parent,      
          'norm'       :prefix_norm,        
          'pn'         :prefix_pn,          
          'Q'          :prefix_Q,           
                                           
          'parent_com' :prefix_parent_com,  
          'norm_com'   :prefix_norm_com,    
          'pn_com'     :prefix_pn_com,      
          'Q_com'      :prefix_Q_com,  

          'parent_doc' :prefix_parent_doc,  
          'norm_doc'   :prefix_norm_doc,    
          'pn_doc'     :prefix_pn_doc,      
          'Q_doc'      :prefix_Q_doc,
 
          'history'    :prefix_history,
          'xref'       :prefix_xref 
           
         }


#name:(Z,natural A)
elements={'p':(1,1),'n':(0,1),'H':(1,1),'HE':(2,4),'LI':(3,7),'BE':(4,9),'B':(5,10),
	'C':(6,12),'N':(7,14),'O':(8,16),'F':(9,19),'NE':(10,20),'NA':(11,23),'MG':(12,24),'AL':(13,27),'SI':(14,28),
        'P':(15,31),'S':(16,32),'CL':(17,35),'AR':(18,40),'K':(19,39),'CA':(20,40),'SC':(21,45),'TI':(22,48),
        'V':(23,51),'CR':(24,52),'MN':(25,55),'FE':(26,56),'CO':(27,59),'NI':(28,59),'CU':(29,64),'ZN':(30,65),
        'GA':(31,70),'GE':(32,73),'AS':(33,75),'SE':(34,79),'BR':(35,80),'KR':(36,84),'RB':(37,85),'SR':(38,88 ),                
        'Y':(39,89),'ZR':(40,91),'NB':(41,93),'MO':(42,96),'TC':(43,98),'RU':(44,101),'RH':(45,103),'PD':(46,106),
        'AG':(47,108),'CD':(48,112),'IN':(49,115),'SN':(50,119),'SB':(51,122),'TE':(52,128),'I':(53,127),'XE':(54,131),
        'CS':(55,133),'BA':(56,137),'LA':(57,139),'CE':(58,140),'PR':(59,141),'ND':(60,144),'PM':(61,145),'SM':(62,150),
        'EU':(63,152),'GD':(64,157),'TB':(65,159),'DY':(66,163),'HO':(67,165),'ER':(68,167),'TM':(69,169),'YB':(70,173),
        'LU':(71,175),'HF':(72178 ),'TA':(73,181),'W':(74,184),'RE':(75,186),'OS':(76,190),'IR':(77,192),'PT':(78,195),
        'AU':(79,197),'HG':(80,201),'TL':(81,204),'PB':(82,207),'BI':(83,209),'PO':(84,209),'AT':(85,210),'RN':(86,222),
        'FR':(87,223),'RA':(88,226),'AC':(89,227),'TH':(90,232),'PA':(91,231),'U':(92,238),'NP':(93,237),'PU':(94,244),
        'AM':(95,243),'CM':(96,247),'BK':(97,247),'CF':(98,251),'ES':(99,252),'FM':(100,257),'MD':(101,258),'NO':(102,259),
        'LR':(103,262),'RF':(104,265),'DB':(105,266),'SG':(106,269),'BH':(107,272),'HS':(108,277),'MT':(109,278),'DS':(110,281),
        'RG':(111,282),'CN':(112,285),'NH':(113,286),'FL':(114,289),'MC':(115,290),'LV':(116,293),'TS':(117,294),'OG':(118,294)};

#uncertainty_limit=25+0.5 #for ENSDF format uncertainty
#uncertainty_limit=99+0.5 #for ENSDF format uncertainty (Balraj)

#UNCERTAINTY_LIMIT=99+0.5
#UNCERTAINTY_LIMIT=25+0.5

global is_lowercase
global UNCERTAINTY_LIMIT

def get_prefix(name):
    global is_lowercase

    if(name not in prefix):
       return ' '

    s=prefix[name]
    if(s[1].upper() not in ['C','D']):
       return s

    try:
       if(is_lowercase):
          pass
    except Exception:
       is_lowercase=True #default: lowercase ENSDF format

    if(is_lowercase==False):
       return s

    return s[0]+s[1].lower()+s[2:]
      
def set_UNCERTAINTY_LIMIT(limit):
    global UNCERTAINTY_LIMIT
    UNCERTAINTY_LIMIT=limit

    return 

def get_UNCERTAINTY_LIMIT():
    return UNCERTAINTY_LIMIT

def set_COMMENT_CASE(case):
    global is_lowercase
    if(case.lower()=='lower'):
       is_lowercase=True
    else:
       is_lowercase=False

    return 

def get_COMMENT_CASE():

    global is_lowercase

    try:
       if(is_lowercase):
          pass
    except Exception:
       is_lowercase=True #default: lowercase ENSDF format

    if(not is_lowercase):
       return 'upper'
    else:
       return 'lower'

def sort_EM_names(EM_names):

    temp=[]
    temp1=[]
    new=[]

    temp=EM_names[:]
    pattern='BE1'
    n=0
    while(len(temp)>0):
      temp1=temp[:]
      for c in temp:
        if(c.find(pattern)>=0):
          new.append(c)
          temp1.remove(c)
      
      temp=temp1[:]
 
      if(pattern.find('BM')>=0):
         pattern=pattern.replace('BM','BE')
         pattern=pattern[0:2]+str(int(pattern[2])+1)
      elif(pattern.find('BE')>=0):
         pattern=pattern.replace('BE','BM')

      n+=1
      if(n>10):
        break

    if(len(new)>0):
      return new

    #return EM_names


level_EM_names=sort_EM_names(level_EM.keys())
gamma_EM_names=sort_EM_names(gamma_EM.keys())


set_UNCERTAINTY_LIMIT(99.5)
#set_COMMENT_CASE('lower')
#init_prefix()




#------------------------------------------------------------ functions
def get_sheetindex(book,Name):

	for i in range (len(book.sheet_names())):

		if book.sheet_by_index(i).name.strip() == Name.strip():
			return i
		else:
			i = -1
	return i

def check_sheetname(book,Name):

	print 'Available Sheets in the Workbook:'
	for i in range (len(book.sheet_names())):
		print '       -> ', book.sheet_by_index(i).name

        text = '(Default sheet to be used: '+Name+')'
	text = text+'\nType the name of the sheet to be used (if none, type "n" to exit):'
	input_name = raw_input(text)
        i =   get_sheetindex(book,input_name)
        if(i<0):
           print 'Sheet='+input_name+' does not exist!'
	return i  

def check_filename(Name):                                        

	#current_dir = os.getcwd()
	#print 'Open file {0} in:\n{1}'.format(Name,current_dir)

	#for i in range (len(os.listdir(current_dir))):
        #
	#	if os.listdir(current_dir)[i] == Name:
	#		return i
	#	else:
	#		i = -1
	#return i

        if(os.path.isfile(Name)):
           return 1
        else:
           return -1

def get_inputfilename(filetype):

	input_filename = raw_input('Input the '+filetype+' file name: ')
	
	fname = input_filename
	return fname

#read a ENSDF-style record string (with uncertainty in bracket)
#and return a list of value string and ENSDF uncertainty string
#It the input string is a text instead of numbers, uncertainty 
#string is returned as empty.
#
def decode_value(value_str):

    s=value_str.strip()
    if(s==''):
        return None

    value=''
    uncertainty=''
    pos=-1
    pos_p=-1
    pos_m=-1
    V=[]
    
    lbracket_count=0
    rbracket_count=0
    lbracket_pos=-1
    rbracket_pos=-1

    lbracket_count=s.count('(')
    rbracket_count=s.count(')')
    lbracket_pos=s.find('(')
    rbracket_pos=s.find(')')


    if(lbracket_count>1 | rbracket_count>1):
        raise Exception("incorrect use of brackets in data entry!")
    if((lbracket_count!=rbracket_count) | (lbracket_pos>rbracket_pos)):
        raise Exception("unmatched brackets in data entry!")
    if((lbracket_pos==rbracket_pos) & (lbracket_pos>=0)):
        raise Exception("empty bracket in data entry!")
    
    if((s[0] in operators) & lbracket_count==1):
        raise Exception("Wrong data entry!")

    #for case like X+1234.5(6) or SN+1234.5(6) or 1234.5+X(6)
    has_offset=False
    pos1=s.find('+')
    pos2=s.find('(')
    if(pos1>0 and pos2>pos1):
       temp_s=s[pos1+1:pos2].strip()


       if(is_number(temp_s)): # X+1234.5(6) or SN+1234.5(6)
          if(s[0].lower() in letters and s[1]=='+'):
             has_offset=True
          elif(s[:2].lower() in ['sn','sp'] and s[2]=='+'):
             has_offset=True
          else:
             has_offset=False
       else: # 1234.5+X(6)
          if(temp_s.lower() in letters or temp_s.lower() in ['sn','sp']):
             temp_s=s[:pos1].strip()
             if(is_number(temp_s)):
                has_offset=True


    #skip non-numerical values which are not uncertainty operators
    if((s[0] not in digits) & (s[0] not in operators) & (s[0] not in pm_op) & (not has_offset)):#case like (2+,3-) or       
        #remove whitespaces in JPI string, like (  2+  )
        if(s[0]=='('):
        #if(lbracket_pos==0):
           index=s.find(' ')
           while(index>0):
             s=s[:index].strip()+s[index:].strip()
             index=s.find(' ')
        
        V.append(s)
        V.append(uncertainty)
        return V

    #skip character string like comments, exception example, "16(AP)" 
    if(lbracket_count!=1):
     for i in range(len(s)):
      if((s[i] not in digits) & (s[i] not in operators) & (s[i] not in pm_op) & (s[i] not in ['(',')',' ','.'])):
           V.append(s)
           V.append(uncertainty)
           #print V
           return V
 
    #check redundant whitespaces, like, "1. 2 (3)", the first " " is wrong and the second is ok
    if(s.find(' ')>0):
        temp=s
        index=temp.rfind(' ')
        while(index>0):
           temp1=temp[:index].strip()
           temp2=temp[index:].strip()
           #if(temp[index+1]!='('):
           if(temp1[-1].isdigit() and temp2[0].isdigit()): #12 34 ( 1 ), only the first " " is wrong
              raise Exception("Warning: check for possible redundant whitespaces in the value string!")
              break
           temp=temp[:index].strip()
           index=temp.rfind(' ')


    if(s[0:2] in operators):
        if(len(s)>2):
            value=s[2:].strip()

        index=operators.index(s[0:2])
        uncertainty=ENSDF_op[index] 
    elif(s[0:1] in operators):
        if(len(s)>1):
            value=s[1:].strip()

        index=operators.index(s[0:1])
        uncertainty=ENSDF_op[index]     
    elif(lbracket_count==0 or lbracket_pos==0):
        value=s.strip()
        uncertainty=''

        #for aymmetric uncertainty, including cases like MR=+1.1+3-4
        pos_p=s[1:].find('+')
        pos_m=s[1:].find('-')
        if((pos_p>0) & (pos_m>0) & (s.find(',')<0)): #exclude cases like '2+,3-
             pos=pos_p
             if(pos_m<pos):
                pos=pos_m
             value=s[0:pos+1]
             uncertainty=s[pos+1:]
    
    else:

        #for normal value string with uncertainty in a bracket
        index=lbracket_pos
        value=s[0:index].strip()
        uncertainty=s[index+1:rbracket_pos].strip()
        if(value.find(' ')>0 and value[0] in pm_op):
           value=value.replace(" ","")
        
        if(is_number(value)):
           if(uncertainty.strip()!='' and not is_number(uncertainty) and uncertainty not in ENSDF_op):
              s1=uncertainty.replace('+','').replace('-','').replace(' ','')
              if(uncertainty.find('+')>0 and uncertainty.find('-')>0 and is_number(s1)):
                 #do nothing
                 uncertainty=uncertainty
              else:
                 value=s.strip()
                 uncertainty=''
        else: #for cases like J|p='5/2+,(7/2+)', exclude cases like '1234.5+X(12)', which is treated normally
           index=value.find('+')
           if((',' in s) or index<=0 or (not has_offset)):#exclude cases like '1234.5+X(12)'  
              value=s.strip()
              uncertainty=''


    #if(value.strip()==''):
    #    raise Exception("No value is given!")

    #remove whitespaces in the middle
    if(len(uncertainty.strip())==0):
       s=value
       index=s.find(' ')
       while(index>0):
          s=s[:index].strip()+s[index:].strip()
          index=s.find(' ')
       value=s

    V.append(value.strip())
    V.append(uncertainty.strip())
    return V
       
#slow? 
def sort_gammas1(gammas):
    i=0
    j=0
    n=len(gammas)
    min_e=1E5
    if(n<=0):
        return

    for i in range(n-1):
        min_e=gammas[i].e()
        for j in range(i+1,n):
            if(gammas[j].e()<min_e):
                min_e=gammas[j].e()
                gammas.insert(i,gammas[j]) 
    
    return gammas         

#slow? 
def sort_levels1(levels):
    i=0
    j=0
    n=len(levels)
    min_e=1E5
    if(n<=0):
        return

    for i in range(n):
        sort_gammas(levels[i]['gammas'])

    i=0
    for i in range(n-1):
        min_e=levels[i].e()
        for j in range(i+1,n):
            if(levels[j].e()<min_e):
                min_e=levels[j].e()
                levels.insert(i,levels[j]) 
    
    return levels  


#still slow
def sort_gammas2(gammas):
    i=0
    j=0
    n=len(gammas)
    min_e=1E5
    min_i=0
    new_gammas=[]
    if(n<=0):
        return [] 

    while(n>0):
        min_e=gammas[0].e()
        min_i=0
        for i in range(1,n):
            if(gammas[i].e()<min_e):
                min_e=gammas[i].e()
                min_i=i
        
        new_gammas.append(gammas[min_i])
        gammas.remove(gammas[min_i])
        n=len(gammas)
                     
    gammas=new_gammas
    return gammas           


#much faster
#7/19/2017
def sort_gammas(gammas):
    return sort_entries(gammas)

#sort level/gamma
#7/19/2017
def sort_entries(entries):
    n=len(entries)
    new_entries=[]
    if(n<=0):
        return [] 

    new_entries.append(entries[0])
    entries.remove(entries[0])
    n=n-1
   
    nold=n
    nnew=1
    while(nold>0):
        e=entries[0].e()
        start=0
        end=len(new_entries)-1
        middle=-1
        pos=-1
        while(True):
            to_break=False
            middle=(start+end)/2
            em=new_entries[middle].e()
            ei=new_entries[start].e()
            ef=new_entries[end].e()
            if(middle==start):#in this case, start+1=end
               to_break=True

            #debug
            #if(len(new_entries)<10):
            #   print '0',[x.e() for x in new_entries]
            #   print e,ei,ef,em,start,end,middle

            if(e>=ef):
               pos=end+1
               to_break=True
            elif(e<ei):
               pos=start
               to_break=True
            elif(e>em):
               start=middle
               pos=middle+1
            elif(e<em):
               end=middle
               pos=middle
            else:
               pos=middle+1
               to_break=True

            if(to_break):
               break
            else:
               continue

        if(pos<0):#should never happen
           pos=len(new_entries)
 
        #debug
        #if(len(new_entries)<10):
        #    print '1',[x.e() for x in new_entries]
        #    print e,pos
            
        new_entries.insert(pos,entries[0])
        entries.remove(entries[0])
        nold=len(entries)
          
        #debug      
        #if(len(new_entries)<10):
        #    print '2',[x.e() for x in new_entries]
        #    print e,pos
    
    entries=new_entries
    return entries 

def sort_levels2(levels):
    
    i=0
    j=0
    n=len(levels)
    min_e=1E5
    min_i=0
    new_levels=[]
    new_gammas=[]
    if(n<=0):
        return []

    for i in range(n):
        new_gammas=sort_gammas(levels[i]['gammas'])
        levels[i]['gammas']=new_gammas

    while(n>0):
        min_e=levels[0].e()
        min_i=0
        for i in range(1,n):
            if(levels[i].e()<min_e):
                min_e=levels[i].e()
                min_i=i
        
        new_levels.append(levels[min_i])
        levels.remove(levels[min_i])
        n=len(levels)
  
    levels=new_levels
    return levels 

#7/19/2017
def sort_levels(levels):

    n=len(levels)
    if(n<=0):
        return []

    new_gammas=[]
    for i in range(n):
        new_gammas=sort_gammas(levels[i]['gammas'])
        levels[i]['gammas']=new_gammas
  
    levels=sort_entries(levels)

    return levels 

#decays is a group of levels with EL=0 and EB(or EA)!=0
def sort_decays(decays):
    
    i=0
    j=0
    n=len(decays)
    min_e=1E5
    min_i=0
    new_decays=[]
    if(n<=0):
        return []

    l0=decays[0]
    if(len(l0['EB'])>0):
      name='EB'
    elif(len(l0['EA'])>0):
      name='EA'
    else:
      return decays

    while(n>0):
        min_e=get_value(decays[0],name)
        min_i=0
        for i in range(1,n):
            e=get_value(decays[i],name)
            if(e<min_e):
                min_e=e
                min_i=i
        
        new_decays.append(decays[min_i])
        decays.remove(decays[min_i])
        n=len(decays)
  
    decays=new_decays
    return decays 

#delays is a group of levels with EP(or IP)!=0
#used by xls2ens
def sort_delays(delays):
    
    i=0
    j=0
    n=len(delays)
    min_e=1E5
    min_i=0
    new_delays=[]
    if(n<=0):
        return []

    l0=delays[0]
    if(len(l0['EDP'])>0):
      name='EDP'
    elif(len(l0['EDN'])>0):
      name='EDN'
    elif(len(l0['EDA'])>0):
      name='EDA'
    elif(len(l0['IP'])>0):
      name='EDP'
    else:
      return delays

    while(n>0):
        min_e=get_value(delays[0],name)
        min_i=0
        for i in range(1,n):
            e=get_value(delays[i],name)
            if(e<min_e):
                min_e=e
                min_i=i
        
        new_delays.append(delays[min_i])
        delays.remove(delays[min_i])
        n=len(delays)
  
    delays=new_delays
    return delays 

def get_value(entry,name):
    if(not isinstance(entry,dict)):
       return -1

    if(name not in entry.keys()):
       return -1

    e_str=entry[name]
    if(not is_number(e_str)):
       return -1

    return float(e_str)

#create a new string of specified length from
#a string by appending whitespaces at the end
#of it.
#if specified length is smaller than the length
#of the old string,store the old string in a 
#comments buffer to be handled later
#if old string is empty, return white spaces with
#size=length
def fill_space(old_str,length):
    
    white_space=' '

    str_length=len(old_str)
    if(str_length>length):
        print 'Warning: string ({0}) is longer than maximum length={1}'.format(old_str,length)

        old_str='$'+old_str
        comment_buffer.append(old_str)
        str_length=0
        old_str=''
        #sys.exit(0)

    new_str=old_str+(length-str_length)*white_space

    return new_str


def fill_space_by_name(old_str,name):
    
    white_space=' '

    str_length=len(old_str)
    length=all_fields[name][1]
    if(str_length>length):
        print 'Warning: string ({0}) is longer than specified length={1}'.format(old_str,length)
        
        comment_buffer.append(old_str)
        str_length=0
        #sys.exit(0)

    new_str=old_str+(length-str_length)*white_space

    return new_str

#wrap a long string with the specified width and prefix and
#label each line at label_pos using 0-9 and a-z
#for ENSDF format, width=80, label_pos=5(start position=0)
#an example of prefix for a level comment record
#prefix=' 35AR CL ' with length=9
# ' 35AR CL'  no label for the first line, for PN comment,use label='2' for the first line
# ' 35AR2CL'  label='2'
def wrap_string(data_str,prefix,width,label_pos):
    
    line_label='1'
    out_str=''
    temp_str='' 
    index=0

    if((data_str=='') & (prefix=='')):
        return ''

    data_str=data_str.replace('\n',' ')

    #DO NOT TRIM 'prefix'
    data_str=data_str.strip()
    
    str_length=len(data_str)
    width=width-len(prefix)


    if(str_length<=width):
        return prefix+data_str

    while(str_length>width):
        if(out_str!=''):
            out_str+='\n'
        
        if(line_label=='1'):
            line_label=prefix[5] #' ' except for PN comment where it is '2'
        
        if(data_str[width]==' '):
            temp_str=prefix+data_str[0:width]
            temp_str=temp_str[:label_pos]+line_label+temp_str[label_pos+1:]
            out_str+=temp_str
            data_str=data_str[width:]
        else:
            index=data_str[:width].rfind(' ')
            if(index<0):
                index=width          
            temp_str=set_length(data_str[0:index],width)
            temp_str=prefix+temp_str
            temp_str=temp_str[:label_pos]+line_label+temp_str[label_pos+1:]            
            out_str+=temp_str
            data_str=data_str[index:]
      
        data_str=data_str.strip()
        str_length=len(data_str)

        if(line_label=='9'):
            line_label='a'
        else:
            if(line_label==' '):
               line_label='1'
            line_label=chr(ord(line_label)+1) 
    
    #last line
    temp_str=prefix+data_str
    temp_str=temp_str[:label_pos]+line_label+temp_str[label_pos+1:]
    out_str+='\n'+temp_str

    return out_str

# get a string from a ENSDF-format data block
def get_string(data_block):
    out_str=''
    for s in data_block:
       out_str+=s[9:].strip(' \r\n')+' '

    return out_str.strip()

def print_value_in_comment(name,value,uncertainty,unit):
    global is_lowercase

    try:
       if(is_lowercase):
          pass
    except Exception:
       print 'Warning: comment case has not been set using set_COMMENT_CASE(case)'
       print '         will use lowercase by default'
       is_lowercase=True #default: lowercase ENSDF format
    
    return print_value_in_ENSDF_format(name,value,uncertainty,unit,is_lowercase) 

def print_value_in_continuation(name,value,uncertainty,unit):
    return print_value_in_ENSDF_format(name,value,uncertainty,unit,False) 

def print_value_in_ENSDF_format(name,value,uncertainty,unit,is_lowercase):

    operators=dict(zip(ENSDF_op,ENSDF_op_lower)) #operator dictionary

    op='='

    data_str=''
    if(value=='' and ((uncertainty!='') or (unit!=''))):
        print 'Warning: no data value in print_value_in_ENSDF_format!'
        return data_str

    name=name.strip()
    value=value.strip()
    uncertainty=uncertainty.strip()
    unit=unit.strip()

    if(name==''):
        op=''

    if(uncertainty in operators.keys()):
        op=operators[uncertainty]  
        uncertainty='' 
    else:
        if(uncertainty!=''): # real uncertainty with digits
            uncertainty=' '+uncertainty

    if(unit!=''):
        unit=' '+unit

    if(len(uncertainty.strip())==0):
       return name+op+value+unit;

    if(is_lowercase):
       data_str=name+op+value+unit+' {I'+uncertainty.strip()+'}'
    else:
       data_str=name+op+value+unit+uncertainty

    return data_str   

#get the power of 'value' with the largest possible base that is not larger than 'limit'.
#used to get the power of real uncertainty value with the ENSDF-format uncertainty limit=25
#e.g., for a real uncertainty=0.000012, ENSDF-format uncertainty=12, power=-6
#                 uncertainty=1234, ENSDF-format uncertainty=12, power=2 
#the argument 'real_value' must be a real float type value, not string, same for 'limit'
def get_power(real_value,limit):
    
    power=0
    value=real_value+0.0
    if(real_value==0):
        return -1000

    if(value<limit):
        while(value<limit):
            value=value*10
            if(value<limit):
                power-=1    
    else:
        while(value>limit):
            value=value/10        
            power+=1

    return power

#format strings of real value and uncertainty to 
#ENSDF format with number of unc digits=unc_digits
#right now, it can only handle symmetric uncertainty.
#ndecimal: number of decimal digits after dot. It applies
#only for the case without uncertainty and value>1)
def format_ENSDF0(value_str,uncertainty_str,unc_ndigits,ndecimal):
    
    #uncertainty_limit=25+0.5 #for ENSDF format uncertainty
    #uncertainty_limit=99+0.5 #for ENSDF format uncertainty (Balraj)
    unc_limit=UNCERTAINTY_LIMIT

    #force one-digit uncertainty
    if(unc_ndigits<2):
      unc_limit=9+0.5

    dot_index=-1
    uncertainty_power=0
    value_power=0
    ndigits_after_decimal=0
    V=[]
     
    value_str=value_str.strip()
    uncertainty_str=uncertainty_str.strip()
    if(is_numerical(uncertainty_str)):
       if(float(uncertainty_str)<=0):
          uncertainty_str=''

    dot_index=value_str.find('.')
    if(dot_index>=0):
       ndigits_after_decimal=len(value_str)-dot_index-1

    if(is_numerical(value_str) and not is_numerical(uncertainty_str)):
      #remove trailing zeros
      value_str=str(float(value_str))

      [n,power]=significant_digits(value_str)

      #python 'format' does not round up at last '5', 
      #it rounds it down, eg, 12.5 round up to 12 not 13
      #but it rounds 12.5000000001 to 13
      value=float(value_str)*(1+1.0E-9)
      
      if(n>1 and '.' in value_str):
        if(abs(value)<1E-3):
          value_str='{0:.1E}'.format(value)
        elif(abs(value)<1):
          if(abs(value)/pow(10,power)>=5):
             value_str='{0:.{1}f}'.format(value,-power)
          else:
             value_str='{0:.{1}f}'.format(value,-power+1)
        else:
          value_str='{0:.{1}f}'.format(value,ndecimal)
     
    #print 'In format_ENSDF',value_str,uncertainty_str
    V_temp=[value_str,uncertainty_str]

    no_change=False
    if((uncertainty_str=='') | (uncertainty_str in operators) | (uncertainty_str in ENSDF_op) | (uncertainty_str in ENSDF_op_lower)):
        no_change=True
   
    if(no_change):
        return V_temp

    try:
        value=float(value_str)*(1+1.0E-9)#python doesn't round 24.5 to 24, but 24.50000000001 to 25
        uncertainty=float(uncertainty_str)
    except ValueError:
        print 'Warning: can\'t convert string to float: {0} {1}'.format(value_str,uncertainty_str)
        return V_temp
  
    uncertainty_power=get_power(uncertainty,unc_limit)
    value_power=get_power(value,9.99999)

    #print 'In format_ENSDF 1',value,uncertainty,value_str,uncertainty_str
    #print 'In format_ENSDF 1',value_power,uncertainty_power,ndigits_after_decimal

    #for case like: 0.09(0.7) (unc_limit=25), value_power=-2,unc_power=-1
    if(value_power<uncertainty_power):
        if(uncertainty_power<0):
           temp=uncertainty/(10**uncertainty_power)+0.01
           if(temp<9.9):
              uncertainty_power=uncertainty_power-1
           value_power=uncertainty_power
        else:
           print 'Warning: please check the real values: (value,uncertainty)=({0},{1})!'.format(value_str,uncertainty_str)
           #print '         value_power={0}, uncertainty_power={1}'.format(value_power,uncertainty_power)
           return V_temp
    

    if(uncertainty_power<=0):
        #for most cases, ndigits_after_decimal=-uncertainty_power, like, 3.12(0.12)
        if(ndigits_after_decimal>-uncertainty_power or (ndigits_after_decimal<-uncertainty_power-1)):#for case like, 1.3456(0.12) or 321.3(+0.56)
           ndigits_after_decimal=-uncertainty_power          
        else:#ndigits_after_decimal=-uncertainty_power-1
           temp=uncertainty*(10**ndigits_after_decimal)+0.001
           #print '*temp=',temp,uncertainty,uncertainty/(10**ndigits_after_decimal)
           if(temp<0.936):#  0.000001(4e-7)
              ndigits_after_decimal=-uncertainty_power
           else:  
              uncertainty_power=-ndigits_after_decimal     
      

        #for case like 3.1+/-0.2, uncertainty power=-2, ndigits_after_decimal=2, so the print out is 3.10 20. This is not quite right!
        #So one need to compare the -uncertainty power with the number of digits after decimal of the value string
        #and take the smaller one as the ndigits_after_decimal and uncertainty_power=-ndigits_after_decimal
        #similar case: 31(2)
        #
        #HOWEVER, expetion case: 0.003+/-0.00045, unc_power=-5 (when limit=99), val_power=-3, nidigits_after_decimal=5.
        #the print out 0.00300 45 is correct. No need for above comparison. 
        #
        #How to distinguish the first case from the second?
        #The problem of the first case is that zero(s) is added at the end of uncertainty, which artificially increases
        #the precision in val_str. But if there is already zero at the end of uncertainty_str, it should be treated as
        #actual precision and the zero(s) should be kept.
        #So, to distinguish the two cases is to see if there is zero at the end of input uncertaint_str
        #Updated on 3/17/2015: no need for above comparisons, just check if there is ending zero in uncertainty_str   
        #                      if yes, ndigits_after_decimail will be by default
        #                      if no, artificially zero could be added to the end of uncertainty_str
        #                             when there is only one non-zero digit in uncertainty_str (for limit=99)
        #                             or when only one non-zero digit and <3 (for limit=25)
        #Updated on 5/6/2015: for case like "2.5+/-0.25", output if "2.50(25)", which is not correct and should be
        #                     be 2.5(3). Still need to compare get_power(unc) and ndigits after decimal of value_str
        #                     so for this case, set uncertainty_power=-ndigits_after_decimal 

#------------------------------------------------------------------
        dot_index=value_str.find('.')
        exp_index=value_str.upper().find('E')
 
        #find the number of digits after decimal point in value_str: n
        exp_power=0
        n=0
        if(exp_index>0):#for value_str in scientific format
          try:
            exp_power=int(value_str[exp_index+1:])
          except ValueError:
            print 'Error in format_ENSDF({0},{1}): wrong scientific format'.format(value_str,uncertainty_str)   
            return V_temp

          if(dot_index>=0 and dot_index<exp_index):
            n=exp_index-dot_index-1

          n=n-exp_power
         
        elif(dot_index>=0):
          n=len(value_str)-dot_index-1
        
        
        #if(n<ndigits_after_decimal and n>0):  #for case like 3.1+/0.2, n=1, ndigits_after_decimal=-uncertainty_power=2
        #   len1=len(value_str)-value_str.find('.')
        #   len2=len(uncertainty_str)-uncertainty_str.find('.')
        #   if(len1==len2): #only when two strings have matching digits after '.', otherwise use default ndigits_after_decimal
        #     ndigits_after_decimal=n                            
        #     uncertainty_power=-ndigits_after_decimal

        #if(n==0 and uncertainty_str.find('.')<0): #for case like 31(2),n=0, uncertainty_power=-1
        #   ndigits_after_decimal=0
        #   uncertainty_power=0

#-----------------------------------------------------------------------   
        #this can replace all above in between '-------------'   
         
        #print 'In format_ENSDF 2',value_str,uncertainty_str,significant_digits(uncertainty_str),value_power,uncertainty_power
        
        #this assures there is only one non-zero digit at the end (including exp format)
        if(uncertainty_str[-1]!='0' and significant_digits(uncertainty_str)[0]==1): 
           len1=len(value_str)-value_str.find('.')
           len2=len(uncertainty_str)-uncertainty_str.find('.')
           if('.' not in value_str): 
              len1=-1
           if('.' not in uncertainty_str):
              len2=-1
           if(len1<len2): #only when val_str has less digits after decimal, otherwise use default ndigits_after_decimal
              if(float(uncertainty_str[-1]+'0')<unc_limit): #this assures the last digit<3 (when limit=25) (always true when limit=99)       
                ndigits_after_decimal-=1                           #eg, 0.1(0.01), len1=1,len2=2
                if(uncertainty_str[-1]>'4'):#uncertainty needs to be rounded
                  ndigits_after_decimal-=1
                uncertainty_power=-ndigits_after_decimal
    else:
        ndigits_after_decimal=value_power-uncertainty_power #this case, uncertainty>UNCERTAINTY_LIMIT.
                                                            #ndigits_after_decimal is for the base in scientific format
    
    #print 'In format_ENSDF 2',value_str,uncertainty_str
    #print 'In format_ENSDF 2',value_power,uncertainty_power  
    ENSDF_uncertainty=uncertainty/(10**uncertainty_power)+0.01 #python doesn't round 24.5 to 24, but 24.55 or 24.505 to 25

    uncertainty_str='{0:.0f}'.format(ENSDF_uncertainty)
    length=len(uncertainty_str)

    #use scientific notation if value<1E-3 or uncertainty>limit
    if(((value<1E-3) & (value!=0)) | (uncertainty>unc_limit)):
        if(value_power<0):#for cases with value<1E-3
          ndigits_after_decimal=ndigits_after_decimal+value_power

        #value_str='{0:.{1}E}'.format(value,ndigits_after_decimal)
        value=value/(10**value_power)

        value_str='{0:.{1}f}E{2}'.format(value,ndigits_after_decimal,value_power)
        index=value_str.find('E')
        
        #remove ending zeros of value and unc if both have ones
        #if((value_str[index-1]=='0') & (uncertainty_str[length-1]=='0') & (uncertainty_str[length-2]>'2')):
        #    if(value_str[index-2]=='.'):
        #        value_str=value_str[:index-2]+value_str[index:]
        #    else:
        #        value_str=value_str[:index-1]+value_str[index:]
        #    uncertainty_str=uncertainty_str[:length-1]
    else:
        value_str='{0:.{1}f}'.format(value,ndigits_after_decimal)

        #remove ending zeros of value and unc if both have ones
        #if((value_str[len(value_str)-1]=='0') & (uncertainty_str[length-1]=='0') &(uncertainty_str[length-2]>'2')):
        #    value_str=value_str[:len(value_str)-1]
        #    uncertainty_str=uncertainty_str[:length-1]        
        #    if(value_str[len(value_str)-1]=='.'):
        #        value_str=value_str[:len(value_str)-1]
  
    V.append(value_str)
    V.append(uncertainty_str)
    return V
   

#format strings of real value and uncertainty to 
#ENSDF format
#right now, it can only handle symmetric uncertainty.
#But it is normal for half-life to have asymmetric uncertainty
#Note that every digit in value_str matters (counted for significant digits, even ending zeros)
#So it is better to process the ending zeros in value_str before calling this function.
def format_ENSDF1(value_str,uncertainty_str,ndecimal):
    return format_ENSDF0(value_str,uncertainty_str,2,ndecimal)

#default: 2-digit uncertainty or 1-digit after decimal in value without uncertainty
def format_ENSDF(value_str,uncertainty_str):
    return format_ENSDF0(value_str,uncertainty_str,2,1)
   
#convert string of ENSDF-fomrat uncertainty to
#string of real uncertainty
#symmetric uncertainty only
#NOTE that the value_str remains unchanged
#And should not be changed, otherwise
#check_uncertainty() could fail.

def convert_ENSDF(value_str,uncertainty_str): 

    V=[]
    power=0

    if((uncertainty_str=='') | (uncertainty_str in ENSDF_op) | (uncertainty_str in operators)):
        V.append(value_str)
        V.append(uncertainty_str)  
        return V
        
    exp_index=value_str.upper().find('E')
    decimal_index=value_str.find('.')
    length=len(value_str)

    if(exp_index==-1): 
        if(decimal_index>=0):
            power=-(length-decimal_index-1)
    else:
        base_str=value_str[:exp_index].strip()
        power=int(value_str[exp_index+1:])
        decimal_index=base_str.find('.')  
        length=len(base_str)
        if(decimal_index>=0):
            power=power-(length-decimal_index-1)

    #print 'convert_ENSDF',value_str,uncertainty_str,power
    uncertainty=float(uncertainty_str)*(10**power)

    uncertainty_str=str(uncertainty)
    V.append(value_str)
    V.append(uncertainty_str)

    return V

#check if an input ENSDF-format (value,uncertainty) pair complies with
#the ENSDF-format convention
#e.g., 1.234(12) is ok
#but 1200(300) is not, for this case, this function will return 
#scientific notation of this pair 
#This function is used to check the format of the uncertainty to be put in level, gamma
#or decay record. Right now it can only check symmetric uncertainty
def check_uncertainty(value_str,uncertainty_str):

    V=[]
    op=''
    if((uncertainty_str=='') | (uncertainty_str in ENSDF_op) | (uncertainty_str in operators)):
        V.append(value_str)
        V.append(uncertainty_str)
        return V

    #skip asymmetric uncertainty
    if((uncertainty_str.find('+')>=0) & (uncertainty_str.find('-')>=0)):
        V.append(value_str)
        V.append(uncertainty_str)
        #print V[0],V[1]
        return V

    try:  
      uncertainty=float(uncertainty_str)
      if(uncertainty==0.0):
        V.append(value_str)
        V.append('')
        return V
      elif(uncertainty<UNCERTAINTY_LIMIT):
        V.append(value_str)
        V.append(uncertainty_str)
        return V
        
    except ValueError:
      V.append(value_str)
      V.append(uncertainty_str)
      return V        

    #for MR like +1.2(3)
    if(value_str[0:1] in pm_op):        
       op=value_str[0:1]
       value_str=value_str[1:]

    #if the uncertainty format is not correct ENSDF format
    #first, convert the input ENSDF-format uncertainty to real uncertainty
    try:
      V=convert_ENSDF(value_str,uncertainty_str)
    except Exception:
      print 'Error in converting ENSDF values to real values in check_uncertainty function:{0},{1}'.format(value_str,uncertainty_str)
     
    #next, format the real uncertainty to correct ENSDF-format if input is not correct.
    #If input is correct, nothing will change  
    value_str=V[0]
    uncertainty_str=V[1]  #ENSDF-format uncertainty
    try:
      V=format_ENSDF(value_str,uncertainty_str)
    except Exception:
      print 'Error in formatting real values back to ENSDF in check_uncertainty function:{0},{1}'.format(value_str,uncertainty_str)

    if(op != ''):
      value_str=op+V[0]
      uncertainty_str=V[1]
      V=[]
      V.append(value_str)
      V.append(uncertainty_str)

    return V

#add values in two ENSDF-formated value str
#return a list of final value string and
#uncertainty string
#example:
#str1=12.3(12), str2=1192.12(5)
#
def str_sum(str1,str2):
    V1=decode_value(str1)
    V2=decode_value(str2)

    #return V_sum1(V1,V2)
    return V_operation(V1,V2,'ADD')

#subtract value in ENSDF-formated value str1
#by the value in str2
#return a list of final value string and
#uncertainty string
def str_subtract(str1,str2):
    V1=decode_value(str1)
    V2=decode_value(str2)

    #return V_subtract1(V1,V2)
    return V_operation(V1,V2,'SUBTRACT')


#multiply values in two ENSDF-formated value str
#return a list of final value string and
#uncertainty string
def str_product(str1,str2):
    V1=decode_value(str1)
    V2=decode_value(str2)

    return V_operation(V1,V2,'MULTIPLY')

def str_divide(str1,str2):
    V1=decode_value(str1)
    V2=decode_value(str2)

    return V_operation(V1,V2,'DIVIDE')

#Input V1,V2 must be
#V[0]=value string
#V[1]=uncertainty string in ENSDF style
#
def V_sum1(V1,V2):

    V=[]
    if(V1==None or V2==None):
      print 'Error: empty string in V_sum function'
      return None

    if((not is_numerical(V1[0])) or (not is_numerical(V2[0]))):
      print 'Error: non-numerical string in V_sum function: '+V1[0]+V2[0]
      return []

    val_str=str(float(V1[0])+float(V2[0]))
    val_str=val_str.strip()
    V.append(val_str)

    val_str1=V1[0].strip()
    val_str2=V2[0].strip()

    unc_str1=V1[1].strip().upper()
    unc_str2=V2[1].strip().upper()

    try:
      unc1=float(convert_ENSDF(val_str1,unc_str1)[1])
      #print 'V1',convert_ENSDF(val_str1,unc_str1)
    except ValueError:
      if(len(unc_str1)==0 or unc_str1 in operators or unc_str1 in ENSDF_op or unc_str1 in ENSDF_op_lower):
        V.append(unc_str1)
        unc1=0
      else:
        print 'Error: wrong uncertainty in V_sum function: '+unc_str1
        return []

    try:
      unc2=float(convert_ENSDF(val_str2,unc_str2)[1])
      #print 'V2',convert_ENSDF(val_str2,unc_str2)
    except ValueError:
      if(len(unc_str2)==0 or unc_str2 in operators or unc_str2 in ENSDF_op or unc_str2 in ENSDF_op_lower):
        if(len(V)==1):
          V.append(unc_str2)
        else:
          V[1]=unc_str2

        unc2=0
      else:
        print 'Error: wrong uncertainty in V_sum function: '+unc_str2
        return []

    if(unc1==0 and len(unc_str1)!=0 and unc2==0 and len(unc_str2)!=0):
        print 'Warning: value strings could be added improperly.'
        print '         plese check the uncertainty: '+unc_str1+unc_str2
        return V
    
    if(unc1<0 or unc2<0):
       print 'Error: negative uncertainty in V_sum function: '+unc_str1+unc_str2
       return []

    unc=math.sqrt(unc1**2+unc2**2)
     
    if(unc>0 and len(V)==1):
      unc_str=str(unc)
      V=format_ENSDF(val_str,unc_str)
   
    #print unc_str1,unc1,unc_str2,unc2
    #print V

    return V

def V_subtract1(V1,V2):

    V=[]
    if(V1==None or V2==None):
      print 'Error: empty string in V_subtract function'
      return None

    if((not is_numerical(V1[0])) or (not is_numerical(V2[0]))):
      print 'Error: non-numerical string in V_subtract function: \'{0},{1}\''.format(V1[0],V2[0])
      return []

    val=float(V1[0])-float(V2[0])
    if(val<0):
      print 'Warning: the final value after subtraction is negative'
      print '         please check if it is expected'

    val_str=str(val)
    val_str=val_str.strip()
    V.append(val_str)

    val_str1=V1[0].strip()
    val_str2=V2[0].strip()

    unc_str1=V1[1].strip().upper()
    unc_str2=V2[1].strip().upper()

    try:
      unc1=float(convert_ENSDF(val_str1,unc_str1)[1])
      #print 'V1',convert_ENSDF(val_str1,unc_str1)
    except ValueError:
      if(len(unc_str1)==0 or unc_str1 in operators or unc_str1 in ENSDF_op or unc_str1 in ENSDF_op_lower):
        V.append(unc_str1)
        unc1=0
      else:
        print 'Error: wrong uncertainty in V_substract function: '+unc_str1
        return []

    try:
      unc2=float(convert_ENSDF(val_str2,unc_str2)[1])
      #print 'V2',convert_ENSDF(val_str2,unc_str2)
    except ValueError:
      if(len(unc_str2)==0 or unc_str2 in operators or unc_str2 in ENSDF_op or unc_str2 in ENSDF_op_lower):
        if(unc_str2[0]=='L'):
          unc_str2[0]='G'
        if(unc_str2[0]=='G'):
          unc_str2[0]='L'
        if(unc_str2[0]=='<'):
          unc_str2[0]='>'
        if(unc_str2[0]=='>'):
          unc_str2[0]='<'
        if(len(unc_str2)>1 and unc_str2[1]=='<'):
          unc_str2[1]='>'
        if(len(unc_str2)>1 and unc_str2[1]=='>'):
          unc_str2[1]='<'

        if(len(V)==1):
          V.append(unc_str2)
        else:
          V[1]=unc_str2

        unc2=0
      else:
        print 'Error: wrong uncertainty in V_substract function: '+unc_str2
        return []

    if(unc1==0 and len(unc_str1)!=0 and unc2==0 and len(unc_str2)!=0):
        print 'Warning: value strings could be added improperly.'
        print '         plese check the uncertainty: \'{0},{1}\''.format(unc_str1,unc_str2)
        return V
    
    if(unc1<0 or unc2<0):
       print 'Error: negative uncertainty in V_subtract function: \'{0},{1}\''.format(unc_str1,unc_str2)
       return []

    unc=math.sqrt(unc1**2+unc2**2)
     
    if(unc>0 and len(V)==1):
      unc_str=str(unc)
      V=format_ENSDF(val_str,unc_str)
   
    #print unc_str1,unc1,unc_str2,unc2
    #print V

    return V


def V_product(V1,V2):
    return


#now it can only handle symmetric uncertainty
def V_operation(V1,V2,op_name):

    V=[]
    val_str=''
    unc_str=''
    op_name=op_name.strip().upper()
    unc_ndigits=1
    ndecimal=1 #number of digits after decimal point. It applies only for values without uncertainty

    if(V1==None or V2==None):
      print 'Error: empty string in {0} function'.format(op_name)
      return None

    if(op_name=='REPLACE'):
      return V2
    elif(op_name=='APPEND'): #append string V2[0] to string V1[0]
      return [V1[0]+V2[0],V1[1]]
    elif(op_name=='PREFIX'): #put V2[0] before V1[0]
      return [V2[0]+V1[0],V1[1]]

    if((not is_numerical(V1[0])) or (not is_numerical(V2[0]))):
      #print 'Warning: non-numerical string in {0} function: \'{1}, {2}\''.format(op_name,V1[0],V2[0])
      #print '         nothing happened to the value: {0}({1})'.format(V1[0],V1[1])
      return ['','']

    val_str1=V1[0].strip()
    val_str2=V2[0].strip()

    unc_str1=V1[1].strip().upper()
    unc_str2=V2[1].strip().upper()
   
    is_limit1=False
    is_limit2=False
    ##########################################
    #first, check the uncertainty strings
    ##########################################
    try:
      unc1=float(convert_ENSDF(val_str1,unc_str1)[1])
      #print 'V1',convert_ENSDF(val_str1,unc_str1)
      if(is_numerical(unc_str1) and len(unc_str1)>1):
        unc_ndigits=2
    except ValueError:
      if(len(unc_str1)==0 or unc_str1 in operators or unc_str1 in ENSDF_op or unc_str1 in ENSDF_op_lower):
        unc1=0
        if(len(unc_str1)!=0):
          unc_str=unc_str1
          is_limit1=True
      elif('+' in unc_str1 and '-' in unc_str1):
        print 'Warning: asymmetrical uncertainty in {0} function: {1}({2}). Will not process it.'.format(op_name,val_str1,unc_str1)
        return V1
      else:
        print 'Error: wrong uncertainty in {0} function: {1}({2})'.format(op_name,val_str1,unc_str1)
        return []


    try:
      unc2=float(convert_ENSDF(val_str2,unc_str2)[1])
      #print 'V2',convert_ENSDF(val_str2,unc_str2)
      if(is_numerical(unc_str2) and len(unc_str2)>1):
        unc_ndigits=2
    except ValueError:
      if(len(unc_str2)==0 or unc_str2 in operators or unc_str2 in ENSDF_op or unc_str2 in ENSDF_op_lower):
        unc2=0
        if(len(unc_str2)!=0):
          unc_str=unc_str2
          is_limit2=True
      elif('+' in unc_str2 and '-' in unc_str2):
        print 'Warning: asymmetrical uncertainty in {0} function: {1}({2}). Will not process it.'.format(op_name,val_str2,unc_str2)
        return V1
      else:
        print 'Error: wrong uncertainty in {0} function: {1}({2})'.format(op_name,val_str2,unc_str2)
        return []

    if(is_limit1 and is_limit2):
        print 'Warning: value strings could be handled improperly.'
        print '         plese check the uncertainty: {0}({1}), {2}({3})'.format(val_str1,unc_str1,val_str2,unc_str2)
        return V
    
    if(unc1<0 or unc2<0):
       print 'Error: negative uncertainty in {0} function: {1}({2}), {3}({4})'.format(op_name,val_str1,unc_str1,val_str2,unc_str2)
       return []

    
    do_unc=False
    #add numerical uncertainty in the final result 
    #only if unc1 and unc2 both are numerical
    if(is_numerical(unc_str1) and is_numerical(unc_str2)):
       do_unc=True

    unc=0
 
    ####################################
    # process the value string
    ####################################
    val1=float(val_str1)
    val2=float(val_str2) 
    if(op_name=='ADD'):
      val=val1+val2
      if(do_unc):
        unc=math.sqrt(unc1**2+unc2**2)
      elif(val_str1.find('.')<0 or val_str2.find('.')<0):
        ndecimal=0

    elif(op_name=='SUBTRACT'):
      val=val1-val2
      if(do_unc):
        unc=math.sqrt(unc1**2+unc2**2)  
      elif(val_str1.find('.')<0 or val_str2.find('.')<0):
        ndecimal=0
 
      if(is_limit2):
        unc_str=reverse_op(unc_str2)

    elif(op_name=='MULTIPLY'):
      val=val1*val2
      if(do_unc and val!=0):
        unc=abs(val)*math.sqrt((unc1/val1)**2+(unc2/val2)**2)   # for (unc1/val1)<<1, (unc2/val2)<<1
      elif(val_str1.find('.')<0 or val_str2.find('.')<0):
        if(val1<=0.5 or val2<=0.5):
           ndecimal=1
        else:
           ndecimal=0
     
    elif(op_name=='DIVIDE'):
      if(val2!=0):
        val=val1/val2
        if(do_unc and val!=0):
          unc=abs(val)*math.sqrt((unc1/val1)**2+(unc2/val2)**2) # for (unc1/val1)<<1, (unc2/val2)<<1

        if(is_limit2):
          unc_str=reverse_op(unc_str2)
        
      else:
        print 'Error: Divided by zero in {0} function: {1} {2}'.format(op_name,V1[0],V2[0]) 
        return []
    elif(op_name=='RECOIL_DECORR'): #val1=EG in keV, val2=mass in amu
      if(val2!=0):
        corr=val1*val1/2.0/val2/931.5/1000 #in keV
        val=val1-corr
        if(do_unc and val>0):
          unc=math.sqrt(unc1**2-(2*unc1/val1*corr)**2-(unc2/val2*corr)**2)
    elif(op_name=='POWER'):
      try:
        val=power(val1,val2)
        #unc=? to be added
      except Exception:
        print 'Error in power({0},{1})'.format(val1,val2)
        return []
    elif(op_name=='EXP'):
      val=exp(val1)
      val2=0
      val_str2=''
      unc_str2=''
      #unc=? to be added
    else:
      print 'Error: wrong operation name in V_operation() function: {0}'.format(op_name)
      return []  
   

    if(val<0):
      print 'Warning: the final value after {0} operation is negative'.format(op_name)
      print ' {0} {1} {2} = {3}'.format(val1,op_name,val2,val)
      print '       Operation will not be done. Please check if it is expected'
      return V1
      #sys.exit(0)

    if(unc>0):
      unc_str=str(unc)

    #val_str=str(val)

    #format keep precision of 6 digits after decimal
    if(val>1e-3):
       val_str='{0:.8f}'.format(val)
    else:
       val_str='{0:.16f}'.format(val)

    #remove trailing zeros to avoid printing 1.30+/-0.20 as 1.30(20) 
    #when the original values has one-digit uncertainty
    #if(unc_ndigits==1):
    #  val_str=str(val)


    val_str=val_str.strip()
    unc_str=unc_str.strip()

    #V=format_ENSDF(val_str,unc_str)
    V=format_ENSDF0(val_str,unc_str,unc_ndigits,ndecimal)

    #print "##",unc_str1,unc1,unc_str2,unc2
    #print "  ",V,val,unc,"***",val_str,unc_str,unc_ndigits,ndecimal

    return V



# check if a line from a ENSDF file contains the  
# specified record, return True if yes 
#
def has_record(line,record_name):
  
  record_name=record_name.strip().upper()

  if(len(line)<10):
    return False
  elif(len(line)<80):
    line=fill_space(line,80)
  
  if(line[5:8]!=get_record_type(record_name)): #eg, '  L', '  G', '  A'
    return False
 
  if('D'+record_name in all_record_names):
    return True

  if(len(record_name)>1 and record_name[1:] in all_record_names):
    return True

  return False


def get_record_type(record_name):

   #line_type: col 6-8 (start=col 1) of each line in ENSDF file
   line_type=''
   if(record_name in level_record_names):
     line_type='  L'
   elif(record_name in gamma_record_names):
     line_type='  G'  
   elif(record_name in beta_record_names):
     line_type='  B'  
   elif(record_name in ec_record_names):
     line_type='  E'  
   elif(record_name in alpha_record_names):
     line_type='  A'  

   return line_type


# get a specified ENSDF record (value+uncertainty) 
# from a line in ENSDF file
#
def get_record(line,record_name):

   V=[] #value,uncertainty,unit
   unit=''

   if(len(line)<10):
     return V
   elif(len(line)<80):
     line=fill_space(line,80)

   record_type=line[5:8]
   if(record_type not in fixed_record_types):
     return V
  
   name=record_name.strip().upper()
   dname='D'+name
   if(not has_record(line,name) or not has_record(line,dname)):
     print 'Error: wrong record name: '+name
     return []
   
   #value starting position and length in ENSDF line
   V_pos=all_fields[name][0]
   V_len=all_fields[name][1]
   if(V_len<0):
     print 'Error: V_len<0 for record '+name
     return []
   
   #uncertainty staring position and length in ENSDF line
   DV_pos=all_fields[dname][0]
   DV_len=all_fields[dname][1]
   if(DV_len<0):
     print 'Error: DV_len<0 for record '+name
     return []

   val_str=line[V_pos-1:V_pos-1+V_len].strip()
   unc_str=line[DV_pos-1:DV_pos-1+DV_len].strip()

   #print line
   #print val_str,unc_str
   #print V_pos,DV_pos,V_len,DV_len
   index=val_str.find(' ')
   if(name=='T' and index>0):
     unit=val_str[index+1:].strip().upper()
     val_str=val_str[:index].strip()

   V.append(val_str)
   V.append(unc_str)
   if(unit!=''):
     V.append(unit)

   return V


def set_record(line,record_name,V):

   #V=[value,uncertainty,unit]
   unit=''

   if(len(line)<8):
     print 'Error: wrong line to set in set_record()'
     print '       nothing has been set'
     return line
   elif(len(line)<80):
     line=fill_space(line,80)
     #print line

   record_type=line[5:8]
   if(record_type not in fixed_record_types or len(V)<2):
     return line
  
   name=record_name.strip().upper()
   dname='D'+name
   if(not has_record(line,name) or not has_record(line,dname)):
     print 'Warning: wrong record name in set_record(): '+name
     print '         nothing has been set'
     return line
  
   #value starting position and length in ENSDF line
   V_pos=all_fields[name][0]
   V_len=all_fields[name][1]
   if(V_len<0):
     print 'Error: V_len<0 for record '+name
     return ''

   #uncertainty staring position and length in ENSDF line
   DV_pos=all_fields[dname][0]
   DV_len=all_fields[dname][1]
   if(DV_len<0):
     print 'Error: DV_len<0 for record '+name
     return ''

   ln=line
   if(record_name=='T' and len(V)>2):
     newline=ln[:V_pos-1]+fill_space(V[0]+' '+V[2],V_len)+fill_space(V[1],DV_len)+ln[DV_pos-1+DV_len:]
   else:
     newline=ln[:V_pos-1]+fill_space(V[0],V_len)+fill_space(V[1],DV_len)+ln[DV_pos-1+DV_len:]
  
   return newline

def reverse_op(op):

    op=op.strip().upper()
    new_op=''
    if(op in operators or op in ENSDF_op or op in ENSDF_op_lower):
      if(op[0]=='L'):
        new_op='G'+(op[1:] if (len(op)>1) else '')
      elif(op[0]=='G'):
        new_op='L'+(op[1:] if (len(op)>1) else '')
      elif(op[0]=='<'):
        new_op='>'+(op[1:] if (len(op)>1) else '')
      elif(op[0]=='>'):
        new_op='<'+(op[1:] if (len(op)>1) else '')
      elif(op=='|<'):
        new_op='|>'
      elif(op=='|>'):
        new_op='|<'
      else:
        new_op=op
    else:
      return ''

    return new_op

def reset_comment_buffer():
    comment_buffer[:]=[]
    return

def set_length(data,length):
   
    if not data:
      return ''

    if(length>len(data)):   
      return data+(length-len(data))*' '

    return data    

def append_column_name(name,column_names):
    if name not in column_names:
       column_names.append(name)

    return

#if name is already in column_names, do nothing
def insert_column_name(index,name,column_names):
    if name not in column_names:
       column_names.insert(index,name)

    return

def find_operator(data_str):
    V=[]
    
    for i in range(len(data_str)):
        if(data_str[i] in operators):
           V.append(i)
           V.append(data_str[i])
           if(data_str[i:i+2] in operators):
              V[1]=data_str[i:i+2]
           break

    if((V!=[]) & (V[0]>0)):
       return V
    
    for i in range(len(data_str)):
        if(i==0):
           continue

        if(len(data_str[i:])>2 & (data_str[i:i+2] in ENSDF_op) & (data_str[i-1]==' ') & (data_str[i+2]==' ')):
           V[0]=i
           V[1]=data_str[i:i+2]

    return V


def convert_ENSDF_op(op):
    for i,c in enumerate(ENSDF_op):
        if(op==c):
           return operators[i]
    
    if(op in operators):
       return op

    return ''

def is_unc_column(name):
    if(len(name)<2):
      return False

    unc_name=name
    val_name=name[1:]
    
    if(unc_name in level_field_names and val_name in level_field_names):
      return True

    if(unc_name in gamma_field_names and val_name in gamma_field_names):
      return True

    return False

def is_val_column(name):
    if(len(name)<1):
      return False

    val_name=name
    unc_name='D'+name
    
    if(unc_name in level_field_names and val_name in level_field_names):
      return True

    if(unc_name in gamma_field_names and val_name in gamma_field_names):
      return True

    return False

def is_odd(s):
    if(not s.isdigit()):
       return False

    v=int(s)%2
    if(v==1):
       return True

    return False
    
def is_even(s):
    if(not s.isdigit()):
       return False

    v=int(s)%2
    if(v==0):
       return True

    return False

def is_number(s):
    try:
        float(s)
        return True
    except ValueError:
        return False

def is_numerical(s):
    try:
        float(s)
        return True
    except ValueError:
        return False

def is_op_name(s):
    op_name=[]
    op_name.extend(math_op_name)
    op_name.extend(text_op_name)
    for i in range(len(op_name)):
        #print i,op_name[i],s
        if(s==op_name[i]):
           return True

    return False

####
# op_command=field_name+'_'+op_name
# op_name: ADD,MULTIPLY,DIVDE,APPEND, see more in Util.py
def is_op_command(s):
    p=s.upper().find('_')
    if(p<=0):
       return False

    name=s.upper()[p+1:].strip()
        
    return is_op_name(name)

def significant_digits(s):
    V=[]
    s=s.strip().upper()
    power=0
    count=0
    n=0
    decimal_pos=-1
    try:
       value=float(s) 
       index=s.find('E')
       if(index>0):
          power=int(s[index+1:])
          s=s[:index].strip()
         
       if('.' not in s):
          if(index<0):
            power=len(s)-1
          return [len(s),power]

       if(s[0]=='+' or s[0]=='-'):
         s=s[1:].strip()

       n=len(s)
       for i in range(n):
         if(s[n-i-1]!='0'):
           s=s[:n-i]
           break
         else:
           continue

       n=len(s)
       for i in range(n):
         if(s[i]!='0' and s[i]!='.'):
           s=s[i:]
           break
         else:
           if(s[i]=='.'):
             decimal_pos=i
           continue
       
       if(decimal_pos>=0):
          power=decimal_pos-i
       

       if('.' in s):
         power=s.find('.')-len(s)+1
         return [len(s)-1,power]
       else:
         return [len(s),power]

    except ValueError:
       return V
 
    return V

######
# calculate weighted average
# parameters:
#   data_points: list of STRINGs of data values each of which
#                is a list of value and uncertainty
#   unc_option:  "ENSDF" for ENSDF format uncertainty
#                "REAL"  for real uncertainty
#   outlier_weight: upper limit of weight for a data point to 
#                   be considered as an outlier
#   return: Average object
def weighted_average(data_points,unc_option='REAL',weight_limit=0.02):
    
    average=Average(data_points)

    vsum=0.0       
    count=0
    wt=0.0
    chi2=0.0
    int_error=0.0
    ext_error=0.0

    wi=[]
    val=[]
    unc=[]
    
    n=len(data_points)
    if(n==0):
       print 'Error: empty entries! Nothing to be weighted averaged.'
       exit(0)
    if(n==1):
       #print 'Warning: Only one data entry and no average is calcualted'
       V=data_points[0]
       if(is_numerical(V[0])): 
          average.value=float(V[0])
          return average
       else:
          return average

   

    for i in range(n):
       V=data_points[i]

       wi.append(0.0)
       val.append(-1.0)
       unc.append(-1.0)       

       if(len(V)<2 or (len(V)==2 and len(V[1])==0)):
           print 'Warning: data point without uncertainty: {0} in weighted averaging. Skipped.'.format(V)
           average.bad_indexes.append(i)
           continue
       if((len(V[0])>0 and is_numerical(V[0])==False) or (len(V[1])>0 and is_numerical(V[1])==False)):
           print 'Warning: data point with non-numerical values: {0} in weighted averaging. Skipped'.format(V[0]+' '+V[1])
           average.bad_indexes.append(i)
           continue

       if(unc_option.strip().upper()=='ENSDF'):      
          V=convert_ENSDF(V[0],V[1])

       val[i]=float(V[0])
       unc[i]=float(V[1])

       if(unc[i]<=0):
          print 'Error: data point with negative uncertainty in {0} in weighted averaging. Please check.'.format(V[0]+' '+V[1])
          exit(0)

       average.good_indexes.append(i)
       
       wi[i]=1.0/(unc[i]*unc[i])
       wt+=wi[i]
       vsum+=val[i]*wi[i]
       count+=1

    if(count==0):
       print 'Warning: no good data points for averaging!'
       return average

    if(wt>0):
          
       average.value=vsum/wt
       average.int_error=math.sqrt(1.0/wt)
       
       if(count==1):
          #print 'Warning: at least two points with uncertainties are '
          #print '         needed for averaging. No average is calculated.'  
          average.ext_error=average.int_error    
          return average


       #find outliers
       temp_count=0
       temp_wt=0.0
       temp_vsum=0.0
       for i in range(count):
          index=average.good_indexes[i]
          average.weights[index]=wi[index]/wt
          if(wi[index]/wt<weight_limit):
             average.outlimit_indexes.append(index)
             continue

          temp_wt+=wi[index]
          temp_vsum+=val[index]*wi[index]
          temp_count+=1

       if(temp_count<=1):
          temp_count=count
          average.outlimit_indexes=[]
       elif(temp_count<count):
          average.value=temp_vsum/temp_wt
          average.int_error=math.sqrt(1.0/temp_wt)            
       
       for i in range(count):
          index=average.good_indexes[i]
          if(index not in average.outlimit_indexes):
             ext_error+=wi[index]/wt*(val[index]-average.value)**2

       average.ext_error=math.sqrt(ext_error/(temp_count-1))
       average.chi2=ext_error*wt/(temp_count-1)
       average.is_good=True

    return average



def unweighted_average(data_points,unc_option='REAL'):

    average=Average(data_points)

    vsum=0.0 
    usum=0.0      
    chi2=0.0
    error=0.0
    count=0

    val=[]
    unc=[]

    n=len(data_points)
    if(n==0):
       print 'Error: empty entries! Nothing to be unweighted averaged.'
       exit(0)
    if(n==1):
       #print 'Warning: Only one data entry and no average is calcualted'
       V=data_points[0]
       if(is_numerical(V[0])): 
          average.value=float(V[0])
          return average
       else:
          return average
    
    
    for i in range(n):
       V=data_points[i]

       val.append(-1.0)
       unc.append(-1.0)  

       if(len(V)<2 or (len(V)==2 and len(V[1])==0)):
           print 'Warning: data point without uncertainty: {0} in unweighted averaging. Skipped.'.format(V)
           average.bad_indexes.append(i)
           continue
       if((len(V[0])>0 and is_numerical(V[0])==False) or (len(V[1])>0 and is_numerical(V[1])==False)):
           print 'Warning: data point with non-numerical values: {0} in unweighted averaging. Skipped'.format(V[0]+' '+V[1])
           average.bad_indexes.append(i)
           continue


       if(unc_option.strip().upper()=='ENSDF'):      
          V=convert_ENSDF(V[0],V[1])

       val[i]=float(V[0])
       unc[i]=float(V[1])

       if(unc[i]<=0):
          print 'Error: data point with negative uncertainty in {0} in unweighted averaging. Please check.'.format(V[0]+' '+V[1])
          exit(0)

       average.good_indexes.append(i)

       vsum+=val[i]
       usum+=unc[i]
       count+=1

    if(count==0):
       print 'Warning: no good data points for averaging!'
       return average


    if(True):
       average.value=vsum/count

       if(count==1):
          #print 'Warning: at least two points with uncertainties are '
          #print '         needed for averaging. No average is calculated.' 
          average.int_error=usum
          average.ext_error=usum
          return average      

       for i in range(count):
          index=average.good_indexes[i]
          
          wi=1.0/count
          error+=wi*(val[index]-average.value)**2
          chi2+=(val[index]-average.value)**2
          average.weights[index]=wi

       average.ext_error=math.sqrt(error/(count-1))
       average.int_error=average.ext_error
       average.chi2=chi2/(count-1)
       average.is_good=True
 
    return average


def average(data_points,avg_option='WEIGHTED',unc_option='REAL',outlier_weight=0.02):
    if(avg_option.upper()=='UNWEIGHTED'):
       return unweighted_average(data_points,unc_option)
    else:
       return weighted_average(data_points,unc_option,outlier_weight)


# calculate weighted average
# parameters:
#   data_points: list of data values each of which
#                is a list of real value and uncertainty
#   return: [average,int_error,ext_error,reduced_chi2]
def weighted_average_real(data_points):
    data_points_str=[]
    for dp in data_points:
       dps=[str(s) for s in dp]
       data_points_str.append(dps)

    return weighted_average(data_points_str)

def unweighted_average_real(data_points):
    data_points_str=[]
    for dp in data_points:
       dps=[str(s) for s in dp]
       data_points_str.append(dps)

    return unweighted_average(data_points_str)

def average_real(data_points,avg_option='WEIGHTED'):
    if(avg_option.upper()=='UNWEIGHTED'):
       return unweighted_average_real(data_points)
    else:
       return weighted_average_real(data_points)    

#return (Z,given A,natural A,symbol)
#if A is not given, given A=-1
#e.g., getZA('P')=(15,-1,31)
#      getZA('38AR')=(18,38,40)
def getZA(nucleus):
    s=nucleus.strip()
   
    AS=''
    name=s
    A=-1
    for i in range(len(s)):
      if(s[i].isalpha()):
        name=s[i:].strip()
        break
      if(s[i].isdigit()):
        AS+=s[i]

    if(AS.isdigit()):
      A=int(AS)
      
    if(name!='p' and name!='n'):
       name=name.upper()
    elif((name=='p' and A>20) or (name=='n' and A>8)): #phosphorus or nitrogen
       name=name.upper()
    elif(A<0):
       A=1

    if(name in elements.keys()):
      v=elements[name]
      if(A>0 and abs(A-v[1])>10):
        print 'Warning: wrong mass number in',nucleus

      return (v[0],A,v[1],name)

    return (-1,10000,10000,name)

#wrap of getZA(nucleus) with extra types of nucleus cominations
def getZA1(s,nucleus_type=''):
    option=nucleus_type.strip().upper()

    if(option=='TARGET' or option==''):
      return getZA(s)

    others={"G":(0,0),"G'":(0,0.01),"NU":(0,0.05),"E":(1,0.1),"E'":(1,0.11),"MU-":(1,0.2),"MU-'":(1,0.21),
            "MU+":(1,0.3),"MU+'":(1,0.31),"PI0":(0,0.4),"PI-":(1,0.4),"PI-'":(1,0.41),"PI+":(1,0.5),"PI+'":(1,0.51),
            };

    beams={"G":(0,0),"E":(1,0.1),"P":(1,1),"N":(0,1),"D":(1,2),"T":(1,3),"A":(2,4),
           "POL G":(0,0),"POL E":(1,0.1),"POL P":(1,1),"POL N":(0,1),"POL D":(1,2),
           "POL T":(1,3),"POL A":(2,4)}

    ejectiles={"P":(1,1),"P'":(1,1.1),"PG":(1,1.2),"P'G":(1,1.3),
               "N":(0,1),"N'":(0,1.1),"NG":(0,1.2),"N'G":(0,1.3),
               "D":(1,2),"D'":(1,2.1),"DG":(1,2.2),"D'G":(1,2.3),
               "T":(1,3),"T'":(1,3.1),"TG":(1,3.2),"T'G":(1,3.3),
               "A":(2,4),"A'":(2,4.1),"AG":(2,4.2),"A'G":(2,4.3)}

  
    if(s in others.keys()):
       v=others[s]
       return (v[0],v[1],v[1],s)
 
    if(option=='BEAM'):
       if(s in beams):
          v=beams[s]
          return (v[0],v[1],v[1],s)
       else:
          return getZA(s)
    elif(option=='EJECTILE'):
       if(s in ejectiles):
          v=ejectiles[s]
          return (v[0],v[1],v[1],s)

       v=getZA(s.lower())
       if(v[0]>=0):
          return v
       
       if(s[0].isalpha()):
          return (-1,0,0,s)
       elif(s[0].isdigit()):
          return (-1,int(s[0]),int(s[0]),s) 
       else:
          return (-1,10000,10000,s)
    else:
       return getZA(s)
   
    return (-1,10000,10000,s)

    
#read lines from a file and strip ending '\r','\n'
def readLines(filename):
    lines=[]
    if(os.path.isfile(filename)):
       f=open(filename)
       filebuffer=f.read()

       if('\r\n' in filebuffer):
          lines=filebuffer.replace('\r\n','\n')
       
       lines=filebuffer.split('\n')

       #if(filename=='A138_bkp.ens'):
       #   print len(lines),len(filebuffer),'\r\n' in filebuffer,'\n' in filebuffer
       #   print lines[-1]


       f.close()
    else:
       print 'Error: File does not exist:',filename
       return []
    
    if(lines==[]):
      print 'Warning: empty file',filename
      return []

    line=lines[-1]
    while(line.strip()==''):
      lines.pop()
      if(len(lines)==0):
        return []
      else:
        line=lines[-1]
 
    line=lines[0]
    while(line.strip()==''):
      lines.remove(line)
      if(len(lines)==0):
        return []
      else:
        line=lines[0]
  
    return lines


#read blocks of lines from a file and strip ending '\r','\n'
#blocks are separated by an empty line
def readBlocks(filename):
    blocks=[]
    block=[]
   
    lines=readLines(filename)#no empty line at begin and end
    for i in range(len(lines)):
       line=lines[i]
       if(line.strip()==''):
          blocks.append(block)
          block=[]

       block.append(line+'\n')


    if(block!=[]):
       blocks.append(block)

    return blocks
          

# clean an ENSDF file by doing nothing 
# except for putting line-ending character
# at column 80
def cleanENSDF(infilename,outfilename=''):
    
    lines=[]
    lines=readLines(infilename)#\r\n or \n is removed

    if(lines==[]):
      return

    if(outfilename!=''):
      outfile=open(outfilename,'w')
    else:
      outfile=open(infilename,'w')

    for i in range(len(lines)):
      line=lines[i].rstrip()
      line='{0:80s}\n'.format(line)
      outfile.write(line)

    return

#************************************************************
#translate an upper-case DSID to lower-case ENSDF format
# e.g., 35CL(P,G)    to {+35}Cl(p,|g)
#       40S B- DECAY to {+40}S |b{+-} decay 
#************************************************************
def translateDSID(DSID):
    type_dict={'B+':'|b{++}','B-':'|b{+-}','EC':'|e','A':'|a'}

    s=DSID

    if(len(s)==0):
       return s

    if((s.find('{')>=0 and s.find('}')>0) or s.find('|')>=0):#DSID already in lower-case ENSDF format
       return s


    lbracket=s.find('(')
    rbracket=s.find(')')
    comma=s.find(',')

        
    if(s.find('DECAY')>0):#decay
       s=s.replace(':',' ').replace('(',' ').replace(')',' ')
       parts=s.split()          
       if(len(parts)<3 or parts[2]!='DECAY'):
          return s.lower()
       
       decay_parent=translateNucleus(parts[0])
       
       decay_type=parts[1]
       for key in type_dict.keys():
          decay_type=decay_type.replace(key,type_dict[key])
       decay_type=decay_type.lower()

       decay_time=''
       decay_time_unit=''
       if(len(parts)>4 and is_numerical(parts[3])):
          decay_time=parts[3]
          decay_time_unit=parts[4].lower()
          if(parts[4]=='US'):
             decay_time_unit='|ms'
       
       s=decay_parent+' '+decay_type+' decay'
       if(len(decay_time)>0):
          s+=' ('+decay_time+' '+decay_time_unit+')'
       
       if(len(parts)>5):
          for part in parts[5:]:
             s+=' '+part
 
       return s
    elif(lbracket>0 and lbracket<comma-1 and comma<rbracket-1):#reaction
       parts=s.split(',')
       s=''
       for i in range(len(parts)):
          part=parts[i]
          options=['TARGET','TARGET']
          NUCs=[]
          delim=''
          if(part.find('(')>0):
             options=['TARGET','BEAM']
             delim='('
          elif(part.find(')')>0):
             options=['EJECTILE','RECOIL']
             delim=')'

          if(len(delim)>0):
             NUCs=part.split(delim)
             for j in range(len(NUCs)):
                option='TARGET'
                if(j<2):
                   option=options[j]
                
                if(NUCs[j].find(':')>=0 or NUCs[j].find(')')>=0 or NUCs[j].find('(')>=0):
                   s+=NUCs[j].lower()
                else: 
                   s+=translateNucleus(NUCs[j],option)
                if(j<len(NUCs)-1):
                   s+=delim   
          else:
             s+=part.lower()
          
          if(i<len(parts)-1):
             s+=','

       return s
    else:
       return s.lower()

    return s

#************************************************************
#translate an upper-case NUCID to lower-case ENSDF format
#  e.g., 35CL to {+35}Cl
#nucleus_type: TARGET, BEAM, EJECTILE
#************************************************************
def translateNucleus(NUCID,nucleus_type='TARGET'):
    temp_dict={'PI+':'|p{++}','PI-':'|p{+-}','PI0':'|p{+0}','MU+':'|m{++}',
               'MU-':'|m{+-}','NU':'|n'}  
    s=NUCID#DO NOT STRIP ending spaces

    if(len(s)==0 or s.find('=')>0):
       return s

    if((s.find('{')>=0 and s.find('}')>0) or s.find('|')>=0):#DSID already in lower-case ENSDF format
       return s
  

    #V[1]=given A in NUCID, V[2]=natural A of the element
    #V[3]=element symbol or NUCID if not an element
    [Z,A,dummy,name]=getZA1(s,nucleus_type)


    #ending 'G' is translated as '|g' only when Z=-1 (not recognized) or Z<=3, like 'G','PG','DG','TG',and 'AG' (in ejectile)
    if(s[-1]=="'"):
       return translateNucleus(s[:-1],nucleus_type)+"'"
    elif(s[-1]==' '):
       return translateNucleus(s[:-1],nucleus_type)+' '
    elif(s[-1]=='G' and Z<10):#for cases like, "AG", "A'G","PG","35SIG","35SI'G","SIG","APG","XG","2PG","2APG", "POL G"
       if(len(s)>2 and s[-2]=="'"):
          return translateNucleus(s[:-2],nucleus_type)+"'|g" #translate "A","P","35SI","SI","AP","X","2P","2AP"
       else:
          return translateNucleus(s[:-1],nucleus_type)+"|g"

    #for temp_NUCID="A","P"(option=1,proton),"AP",X","2P","2AP", "POL ". set temp_NUCID as name
 
    #print Z,A,dummy,name

    translated=''
    if(Z<=2 and s.find('HE')<0):#translated 'A' as |a (alpha) and 'G' as |g (gamma) in cases like 'AG','2APG' in ejectiles
       for i in range(len(s)):
          if(s[i]=='A' or s[i]=='G'):
             translated+='|'
         
          translated+=s[i].lower()

       if(translated=='x'):
          return 'X'
       elif(translated=='hi'):
          return 'HI'       
    elif(Z>=2 and A>=Z):#regular nuceus like 3HE,35CL
       name=name.upper()[0]+name.lower()[1:]
       translated='{{+{0}}}{1}'.format(A,name)
       return translated
    elif(Z>0 and A<0 and s.isalpha()):#CL
       s=s.upper()[0]+name.lower()[1:]
       return s
    else:
       translated=s.lower()
    
    for key in temp_dict:
       if(translated.find(key.lower())>=0):
          translated=translated.replace(key.lower(),temp_dict[key])

    return translated


class Average(object):

    def __init__(self,data_points=[]):
        self.data_points=[]
        self.weights=[]
        self.value=0
        self.int_error=0
        self.ext_error=0
        self.chi2=0

        self.outliers=[]
        self.outlier_indexes=[]

        self.outlimit_indexes=[]#for data points below weight limits

        #all=good+bad
        #good=points_below_weight_limit+used_for_average
        self.bad_indexes=[]#data points without uncertainty or non-numerical value or uncertainty
        self.good_indexes=[]

        self.summary=''
        self.comments=[]

        self.is_good=False
        if(data_points!=[]):
           self.setDataPoints(data_points)

    def setDataPoints(self,data_points):
        self.data_points=[]
        self.data_points.extend(data_points)
        for i in range(len(data_points)):
           self.weights.append(0.0)

    def addDataPoint(self,data_point):
        self.data_points.append(data_point)
        self.weights.append(0.0)


#!/usr/bin/env python

# Contains all information of the header 
# in ENSDF file
# Jun Chen
# Dec,2013

#updates
# 01/09/2014: add parent, Norm and PN records
# 01/06/2016: add Config class to store all static variables
# 07/19/2017: add functions e(),de(),es() for Parent class


#################
### CLASS parent
class Parent(dict):
    def __init__(self):

        for c in parent_field_names:
            if(c in ['CP','PDOC']):
               self[c]=[]
            else:
               self[c]='' 

        self['X']=0.1

    def es(self):
        return self['EP'].strip()

    def e(self):
        e_str=self['EP'].strip()  
 
        if(len(e_str)>0 and e_str[0]=='(' and e_str[-1]==')'):
           e_str=e_str[1:-1]
      
        if not is_number(e_str):
           pos=e_str.find('+')

           
           if(pos<=0):
             if(e_str.lower() in letters):
                return self['X']
             else:
                return -1
           else:
             temp_str=e_str[:pos].strip()
             if not is_number(temp_str):
               temp_str=e_str[pos+1:].strip()

               if is_number(temp_str):
                  return float(temp_str)+self['X'];
               elif(temp_str.lower() in letters):
                  return self['X']
               else:
                  return -1
             else:           
               return float(temp_str)+self['X'];
        else:
           return float(e_str) 

    def de(self):

        e_str=self['EP'].strip()
        de_str=self['DEP'].strip()  

        if not is_number(e_str) or not is_number(de_str):
            return -1

        V=convert_ENSDF(e_str,de_str)
        return float(V[1]) 

    def print_ENSDF(self,NUCID):
        data_str=''
        data_str+=self.print_record(NUCID)
        data_str+=self.print_comment(NUCID)
        return data_str

    def print_record(self,NUCID):
        
        data_str=''
        continuation=''
        prefix=''
        
        prefix=NUCID+get_prefix('parent')
        data_str+=prefix
        V=[] 
        
        #store data entries that can not fill in their desinated spaces 
        #and are to be put in the comments instead (Util.comment_buffer)
        reset_comment_buffer()
        #energy
        value=self['EP']
        uncertainty=self['DEP']

        V=check_uncertainty(value,uncertainty)

        data_str+=fill_space(V[0],parent_fields['EP'][1])
        data_str+=fill_space(V[1],parent_fields['DEP'][1])

        #JPI
        data_str+=fill_space(' '+self['JPA'],parent_fields['JPA'][1]) #add a whitespace to separate it from DEP field

        #half-life
        value=self['TP']
        uncertainty=self['DTP']
        V=check_uncertainty(value,uncertainty)
        if((self['TP']=='') & (self['TPU']=='') & (self['DTP']=='')):
            data_str+=fill_space(' ',parent_fields['TP'][1]+parent_fields['DTP'][1])
        elif((self['TP']!='') & (self['TPU']!='')):
            data_str+=fill_space(V[0]+' '+self['TPU'].upper(),parent_fields['TP'][1])
            data_str+=fill_space(V[1],parent_fields['DTP'][1])
        elif(self['TP'].upper()=='STABLE'):
            data_str+=fill_space(V[0],parent_fields['TP'][1]+parent_fields['DTP'][1])
        else:
            print 'Error: wrong parent half-life record: ',self['TP']+' '+self['TPU']+' '+self['DTP']

        #col 56-64: blank
        value=' '      
        data_str+=fill_space(value,9)
       
        #QP
        value=self['QP']
        uncertainty=self['DQP']
        V=check_uncertainty(value,uncertainty)
        data_str+=fill_space(V[0],parent_fields['QP'][1])
        data_str+=fill_space(V[1],parent_fields['DQP'][1])

        #add the data that do not fit in the space to comments to be printed later
        #in "print_comment"
        if comment_buffer:
            comments=self['CP']
            comment_buffer.extend(comments)
            self['CP']=[]
            self['CP'].extend(comment_buffer)

        return data_str+'\n'

    def print_comment(self,NUCID):

        data_str=''

        comments=self['CP']
        if not comments:
            return ''

        docu=self['PDOC']
        comments=self['CP']
        if (not comments and not docu):
            return ''

        prefix=NUCID+get_prefix('parent_com')
        
        #right now, this method can only handle comments,starting with 'E$', 'T$', 'J$', '$' and so on        
        for c in comments:
            data_str+=wrap_string(c,prefix,80,5)#80: line width, 5: label position (starting position=0)
            data_str+='\n'

        prefix=NUCID+get_prefix('parent_doc')
        for c in docu:
            data_str+=wrap_string(c,prefix,80,5)#80: line width, 5: label position (starting position=0)
            data_str+='\n'

        return data_str


##################
### CLASS NRecord
class NRecord(dict):
    def __init__(self):

        for c in norm_field_names:
            if(c in ['CN','NDOC']):
               self[c]=[]
            else:
               self[c]='' 

    def print_ENSDF(self,NUCID):
        data_str=''
        data_str+=self.print_record(NUCID)
        data_str+=self.print_comment(NUCID)
        return data_str

    def print_record(self,NUCID):
        
        data_str=''
        continuation=''
        prefix=''
        
        prefix=NUCID+get_prefix('norm')
        data_str+=prefix
        V=[] 
        
        #store data entries that can not fill in their desinated spaces 
        #and are to be put in the comments instead (Util.comment_buffer)
        reset_comment_buffer()

        #NR
        value=self['NR']
        uncertainty=self['DNR']

        V=check_uncertainty(value,uncertainty)

        data_str+=fill_space(V[0],norm_fields['NR'][1])
        data_str+=fill_space(V[1],norm_fields['DNR'][1])

        #NT
        value=self['NT']
        uncertainty=self['DNT']

        V=check_uncertainty(value,uncertainty)

        data_str+=fill_space(V[0],norm_fields['NT'][1])
        data_str+=fill_space(V[1],norm_fields['DNT'][1])

        #BR
        value=self['BR']
        uncertainty=self['DBR']

        V=check_uncertainty(value,uncertainty)

        data_str+=fill_space(V[0],norm_fields['BR'][1])
        data_str+=fill_space(V[1],norm_fields['DBR'][1])

        #NB
        value=self['NB']
        uncertainty=self['DNB']

        V=check_uncertainty(value,uncertainty)

        data_str+=fill_space(V[0],norm_fields['NB'][1])
        data_str+=fill_space(V[1],norm_fields['DNB'][1])

        #NP
        value=self['NP']
        uncertainty=self['DNP']

        V=check_uncertainty(value,uncertainty)

        data_str+=fill_space(V[0],norm_fields['NP'][1])
        data_str+=fill_space(V[1],norm_fields['DNP'][1])

        #add the data that do not fit in the space to comments to be printed later
        #in "print_comment"
        if comment_buffer:
            comments=self['CN']
            comment_buffer.extend(comments)
            self['CN']=[]
            self['CN'].extend(comment_buffer)

        return data_str+'\n'

    def print_comment(self,NUCID):

        data_str=''

        docu=self['NDOC']
        comments=self['CN']
        if (not comments and not docu):
            return ''

        prefix=NUCID+get_prefix('norm_com')
        
        #right now, this method can only handle comments,starting with 'E$', 'T$', 'J$', '$' and so on        
        for c in comments:
            data_str+=wrap_string(c,prefix,80,5)#80: line width, 5: label position (starting position=0)
            data_str+='\n'

        prefix=NUCID+get_prefix('norm_doc')
        for c in docu:
            data_str+=wrap_string(c,prefix,80,5)#80: line width, 5: label position (starting position=0)
            data_str+='\n'

        return data_str


###################
### CLASS PNRecord
class PNRecord(dict):
    def __init__(self):

        for c in pn_field_names:
            if(c in ['CPN','PNDOC']):
               self[c]=[]
            else:
               self[c]=''

    def print_ENSDF(self,NUCID):
        data_str=''
        data_str+=self.print_record(NUCID)
        data_str+=self.print_comment(NUCID)
        return data_str

    def print_record(self,NUCID):
        
        data_str=''
        continuation=''
        prefix=''
        
        prefix=NUCID+get_prefix('pn')
        data_str+=prefix
        V=[] 
        
        #store data entries that can not fill in their desinated spaces 
        #and are to be put in the comments instead (Util.comment_buffer)
        reset_comment_buffer()

        #NR*BR
        value=self['NRBR']
        uncertainty=self['DNRBR']

        V=check_uncertainty(value,uncertainty)

        data_str+=fill_space(V[0],pn_fields['NRBR'][1])
        data_str+=fill_space(V[1],pn_fields['DNRBR'][1])

        #NT*BR
        value=self['NTBR']
        uncertainty=self['DNTBR']

        V=check_uncertainty(value,uncertainty)

        data_str+=fill_space(V[0],pn_fields['NTBR'][1])
        data_str+=fill_space(V[1],pn_fields['DNTBR'][1])

        #col 32-41: blank
        value=' '
        data_str+=fill_space(value,10)

        #NB*BR
        value=self['NBBR']
        uncertainty=self['DNBBR']

        V=check_uncertainty(value,uncertainty)

        data_str+=fill_space(V[0],pn_fields['NBBR'][1])
        data_str+=fill_space(V[1],pn_fields['DNBBR'][1])

        #NP
        value=self['NP']
        uncertainty=self['DNP']

        V=check_uncertainty(value,uncertainty)

        data_str+=fill_space(V[0],pn_fields['NP'][1])
        data_str+=fill_space(V[1],pn_fields['DNP'][1])

        #col 65-76: blank
        value=' '
        data_str+=fill_space(value,12)

        #PNCOM: col 77
        data_str+=fill_space(self['PNCOM'],pn_fields['PNCOM'][1])             

        #PNOPT: col 78
        data_str+=fill_space(self['PNOPT'],pn_fields['PNOPT'][1])             

        #add the data that do not fit in the space to comments to be printed later
        #in "print_comment"
        if comment_buffer:
            comments=self['CPN']
            comment_buffer.extend(comments)
            self['CPN']=[]
            self['CPN'].extend(comment_buffer)

        return data_str+'\n'

    def print_comment(self,NUCID):

        data_str=''

        docu=self['PNDOC']
        comments=self['CPN']
        if (not comments and not docu):
            return ''

        prefix=NUCID+get_prefix('pn_com')
        
        #right now, this method can only handle comments,starting with 'E$', 'T$', 'J$', '$' and so on        
        for c in comments:
            data_str+=wrap_string(c,prefix,80,5)#80: line width, 5: label position (starting position=0)
            data_str+='\n'

        prefix=NUCID+get_prefix('pn_doc')
        for c in docu:
            data_str+=wrap_string(c,prefix,80,5)#80: line width, 5: label position (starting position=0)
            data_str+='\n'

        return data_str

##################
### CLASS QRecord
class QRecord(dict):
    def __init__(self):

        for c in Q_field_names:
            if(c in ['CQ','QDOC']):
               self[c]=[]
            else:
               self[c]='' 

    def print_ENSDF(self,NUCID):
        data_str=''
        data_str+=self.print_record(NUCID)
        data_str+=self.print_comment(NUCID)
        return data_str

    def print_record(self,NUCID):
        
        data_str=''
        continuation=''
        prefix=''
        
        prefix=NUCID+get_prefix('Q')
        data_str+=prefix
        V=[] 
        
        #store data entries that can not fill in their desinated spaces 
        #and are to be put in the comments instead (Util.comment_buffer)
        reset_comment_buffer()

        #Q-value
        value=self['Q']
        uncertainty=self['DQ']

        V=check_uncertainty(value,uncertainty)

        data_str+=fill_space(V[0],Q_fields['Q'][1])
        data_str+=fill_space(V[1],Q_fields['DQ'][1])

        #SN
        value=self['SN']
        uncertainty=self['DSN']

        V=check_uncertainty(value,uncertainty)

        data_str+=fill_space(V[0],Q_fields['SN'][1])
        data_str+=fill_space(V[1],Q_fields['DSN'][1])

        #SP
        value=self['SP']
        uncertainty=self['DSP']

        V=check_uncertainty(value,uncertainty)

        data_str+=fill_space(V[0],Q_fields['SP'][1])
        data_str+=fill_space(V[1],Q_fields['DSP'][1])

        #QA
        value=self['QA']
        uncertainty=self['DQA']

        V=check_uncertainty(value,uncertainty)

        data_str+=fill_space(V[0],Q_fields['QA'][1])
        data_str+=fill_space(V[1],Q_fields['DQA'][1])

        #QREF
        value=self['QREF']
        data_str+=fill_space(value,Q_fields['QREF'][1])

        #add the data that do not fit in the space to comments to be printed later
        #in "print_comment"
        if comment_buffer:
            comments=self['CQ']
            comment_buffer.extend(comments)
            self['CQ']=[]
            self['CQ'].extend(comment_buffer)

        return data_str+'\n'

    def print_comment(self,NUCID):

        data_str=''
        docu=self['QDOC']
        comments=self['CQ']
        if (not comments and not docu):
            return ''

        prefix=NUCID+get_prefix('Q_com')
        
        #right now, this method can only handle comments,starting with 'E$', 'T$', 'J$', '$' and so on        
        for c in comments:
            data_str+=wrap_string(c,prefix,80,5)#80: line width, 5: label position (starting position=0)
            data_str+='\n'

        prefix=NUCID+get_prefix('Q_doc')
        for c in docu:
            data_str+=wrap_string(c,prefix,80,5)#80: line width, 5: label position (starting position=0)
            data_str+='\n'

        return data_str

################
### CLASS Config
class Config():
    newline=False
    delay_type='' #for delayed-partice, 'P','N','A' or empty for prompt
    name_dict={}
    keyno_dict={}
    unit_dict={}


    #get alternative or relabelling names for: LCD1, LCD2, ..., GCD1, GCD2, ...
    @staticmethod
    def get_name(colname):
        name=colname
        try:
          name=Config.name_dict[colname]
        except Exception as e:
          pass
         
        return name  


    #get the keynumber to be put at the end of values in column: LCD1, LCD2, ..., GCD1, GCD2, ...
    @staticmethod
    def get_keyno(colname):
        name=colname
        keyno=''
        try:
          keyno=Config.keyno_dict[colname]
        except Exception as e:
          pass
         
        return keyno

    #get the unit for values in column: LCD1, LCD2, ..., GCD1, GCD2, ...
    @staticmethod
    def get_unit(colname):
        name=colname
        unit=''
        try:
          unit=Config.unit_dict[colname]
        except Exception as e:
          pass
         
        return unit

    @staticmethod
    def reset():
        Config.name_dict={}
        Config.keyno_dict={}
        Config.unit_dict={}

################
### CLASS Header
class Header(object):
    def __init__(self):
        self.nuclide=''
        self.reaction=''
        self.nsr=''
        self.reference=''
        self.compiler=''
        self.evaluators=[]
        self.history=[]
        self.general_comments=[]  #general comments to be put at the top of output file
        self.level_comments=[]    #comments for 'cL' or 'CL'
        self.gamma_comments=[]    #comments for 'cG' or 'CG'
        self.other_comments=[]    #comments starting with '$'
        self.parent=None          #parent record for decay dataset
        self.norm=None            #N record for decay dataset
        self.pn=  None            #PN record for dataset with gamma-rays
        self.Q =  None            #Q record
        self.XREFs=[]             #XREF list in Adopted dataset
#!/usr/bin/env python

# Contains all information of a gamma 
# in ENSDF file
# Jun Chen
# Dec,2013

#Update:
# 07/16/2017: add functions for getting lines in ENSDF files


class Gamma(dict):

    def __init__(self):

        for c in gamma_field_names:
            if(c in gamma_comment_names):
              self[c]=[]
            else:
              self[c]='' 

        self['ilevel']=None
        self['flevel']=None
        self['X']=0.1 #for gamma with unknown energy
                    
        self.lines=[]
                
    def es(self):
        return self[eg_field_name].strip()

    def e_old(self):

        e_str=self[eg_field_name].strip()
        if(len(e_str)>0 and e_str[0]=='(' and e_str[-1]==')'):
           e_str=e_str[1:-1]
        
        if not is_number(e_str):
           return -1
        else:
           return float(e_str) 

    def e(self):
        e_str=self[eg_field_name].strip()  
 
        if(len(e_str)>0 and e_str[0]=='(' and e_str[-1]==')'):
           e_str=e_str[1:-1]
      
        if not is_number(e_str):
           pos=e_str.find('+')

           
           if(pos<=0):
             if(e_str.lower() in letters):
                return self['X']
             else:
                return -1
           else:
             temp_str=e_str[:pos].strip()
             if not is_number(temp_str):
               temp_str=e_str[pos+1:].strip()

               if is_number(temp_str):
                  return float(temp_str)+self['X'];
               elif(temp_str.lower() in letters):
                  return self['X']
               else:
                  return -1
             else:           
               return float(temp_str)+self['X'];
        else:
           return float(e_str) 

    def de(self):

        e_str=self[eg_field_name].strip()
        de_str=self[deg_field_name].strip()  

        if not is_number(e_str) or not is_number(de_str):
            return -1

        V=convert_ENSDF(e_str,de_str)
        return float(V[1]) 

    def ri(self):
        return self.get_value("RI")[0]

    def dri(self):
        return self.get_value("RI")[1]

    def cc(self):
        return self.get_value("CC")[0]

    def dcc(self):
        return self.get_value("CC")[1]

    def get_value(self,name):

        V=[-1.0,-1.0]
        V_S=[]
        name=name.upper()
        try:
          val_str=self[name].strip()
          name='D'+name
          unc_str=self[name].strip()
        except KeyError:
          print 'Error: No value for key: {0}!'.format(name)
          exit(0)

        if not is_number(val_str):
           return V

        if not is_number(unc_str):
           V[0]=float(val_str)
           return V

        try:
           V_S=convert_ENSDF(val_str,unc_str)
           V[0]=float(V_S[0])
           V[1]=float(V_S[1])
           return V
        except ValueError:
           print 'Error: can not convert ({0},{1}) to float.\n'.format(val_str,unc_str)
           exit(0)
   
        return V  


    def lines(self):
        return self.lines
    
    def lineAt(self,i):
        if(len(self.lines)>0):
            return self.lines[i]
        
        return ''

    def nlines(self):
        return len(self.lines)
    
###########################################################
### print functions:
### only for the excel2ensdf program
###########################################################

    def print_ENSDF(self,NUCID):

        data_str=''
        data_str+=self.print_gamma(NUCID)
        
        if(Config.newline):
           data_str+=self.print_GCD1(NUCID)
           data_str+=self.print_GCD2(NUCID)
           data_str+=self.print_GCD3(NUCID)
        else:
           data_str+=self.print_GCD(NUCID)
     
        data_str+=self.print_EM(NUCID)
        data_str+=self.print_UDD(NUCID)
        data_str+=self.print_ECC(NUCID)
        data_str+=self.print_angular(NUCID)
        data_str+=self.print_DCO(NUCID)
        data_str+=self.print_POL(NUCID)
        data_str+=self.print_comment(NUCID)

        return data_str


    def print_gamma(self,NUCID):
        
        data_str=''
        continuation=''
        prefix=''
        space=''  
        len_temp=0

        #store data entries that can not fill in their desinated spaces 
        #and are to be put in the comments instead (Util.comment_buffer)
        reset_comment_buffer()

        prefix=NUCID+get_prefix('gamma')
        data_str+=prefix
        
        #energy
        value=self['EG']
        uncertainty=self['DEG']
        V=check_uncertainty(value,uncertainty)
        data_str+=fill_space(V[0],gamma_fields['EG'][1])
        data_str+=fill_space(V[1],gamma_fields['DEG'][1])
        len_temp=len(V[1])

        #intensity
        space=''
        value=self['RI']
        uncertainty=self['DRI']
        V=check_uncertainty(value,uncertainty)
        if(len_temp==2):#add a whitespace to separate it from DEG field
          space=' '
        data_str+=fill_space(space+V[0],gamma_fields['RI'][1])
        len_temp=len(space+V[0])

        space=''
        if(len_temp==gamma_fields['RI'][1] and len(V[1])<gamma_fields['DRI'][1]):
          space=' '
        data_str+=fill_space(space+V[1],gamma_fields['DRI'][1])

        #multi-polarity
        data_str+=fill_space(self['MUL'],gamma_fields['MUL'][1])

        #print 'MR'
        #mixing ratios
        value=self['MR']
        uncertainty=self['DMR']
        #print value,uncertainty
        V=check_uncertainty(value,uncertainty)
        #print value,uncertainty,V[0],V[1]
        data_str+=fill_space(V[0],gamma_fields['MR'][1])
        data_str+=fill_space(V[1],gamma_fields['DMR'][1]) 

        #conversion coefficient
        value=self['CC']
        uncertainty=self['DCC']
        V=check_uncertainty(value,uncertainty)
        data_str+=fill_space(V[0],gamma_fields['CC'][1])
        data_str+=fill_space(V[1],gamma_fields['DCC'][1]) 

        #total intensity
        value=self['TI']
        uncertainty=self['DTI']
        V=check_uncertainty(value,uncertainty)
        data_str+=fill_space(V[0],gamma_fields['TI'][1])
        data_str+=fill_space(V[1],gamma_fields['DTI'][1]) 

        #final level 'FL'
        if(self['FL']!=''):
            prefix=NUCID+get_prefix('gamma_FLAG')
            continuation=prefix+'FL='+self['FL']

        #flags
        if(len(self['GFLAG'])>1):
            data_str+=self['GFLAG'][0]
            prefix=NUCID+get_prefix('gamma_FLAG')   
            if(continuation!=''):
                continuation+='\n'
            continuation+=prefix+'FLAG='+self['GFLAG'][1:]
        else:
            data_str+=' ' if(self['GFLAG']=='') else self['GFLAG'][0]           

        #coincidence & question mark
        if((self['GCOIN']!='') & (self['GCOIN'].upper()=='C')):
            data_str+='C ' #column 78 and 79
        else:
            data_str+='  ' #add two empty spaces for column 78 and 79 in ENSDF file
 
        data_str+=fill_space(self['GQUE'],1)

        if((data_str!='') & (continuation!='')):
            data_str+='\n'+continuation

        #add the data that do not fit in the space to comments to be printed later
        #in "print_comment"
        if comment_buffer:
            comments=self['CG']
            comment_buffer.extend(comments)
            self['CG']=[]
            self['CG'].extend(comment_buffer)

        #calculated lines marked with 'S'
        if(len(self['SG'])>0):
            prefix=NUCID+'S G '
            for c in self['SG']:
               data_str+='\n'+wrap_string(c,prefix,80,5)#80: line width, 5: label position (starting position=0)

        return data_str+'\n'

    def print_gamma1(self,NUCID):
        
        data_str=''
        continuation=''
        prefix=''

        #store data entries that can not fill in their desinated spaces 
        #and are to be put in the comments instead (Util.comment_buffer)
        reset_comment_buffer()

        prefix=NUCID+get_prefix('gamma')
        data_str+=prefix
        
        #energy
        value=self['EG']
        uncertainty=self['DEG']
        V=check_uncertainty(value,uncertainty)
        data_str+=fill_space_by_name(V[0],'EG')
        data_str+=fill_space(V[1],'DEG')

        #intensity
        value=self['RI']
        uncertainty=self['DRI']
        V=check_uncertainty(value,uncertainty)
        data_str+=fill_space(V[0],'RI')
        data_str+=fill_space(V[1],'DRI')
       
        #multi-polarity
        data_str+=fill_space(self['MUL'],'MUL')

        #print 'MR'
        #mixing ratios
        value=self['MR']
        uncertainty=self['DMR']
        #print value,uncertainty
        V=check_uncertainty(value,uncertainty)
        #print value,uncertainty,V[0],V[1]
        data_str+=fill_space(V[0],'MR')
        data_str+=fill_space(V[1],'DMR') 

        #conversion coefficient
        value=self['CC']
        uncertainty=self['DCC']
        V=check_uncertainty(value,uncertainty)
        data_str+=fill_space(V[0],'CC')
        data_str+=fill_space(V[1],'DCC') 

        #total intensity
        value=self['TI']
        uncertainty=self['DTI']
        V=check_uncertainty(value,uncertainty)
        data_str+=fill_space(V[0],'TI')
        data_str+=fill_space(V[1],'DTI') 

        #final level 'FL'
        if(self['FL']!=''):
            prefix=NUCID+get_prefix('gamma_FLAG')
            continuation=prefix+'FL='+self['FL']

        #flags
        if(len(self['GFLAG'])>1):
            data_str+=self['GFLAG'][0]
            prefix=NUCID+get_prefix('gamma_FLAG')
            if(continuation!=''):
                continuation+='\n'
            continuation+=prefix+'FLAG='+self['GFLAG'][1:]
        else:
            data_str+=' ' if(self['GFLAG']=='') else self['GFLAG'][0]           

        #question mark
        data_str+='  ' #add two empty spaces for column 78 and 79 in ENSDF file
        data_str+=fill_space(self['GQUE'],1)

        if((data_str!='') & (continuation!='')):
            data_str+='\n'+continuation

        #add the data that do not fit in the space to comments to be printed later
        #in "print_comment"
        if comment_buffer:
            comments=self['CG']
            comment_buffer.extend(comments)
            self['CG']=[]
            self['CG'].extend(comment_buffer)
         
        data_str+='\n'

        #calculated lines marked with 'S'
        if(len(self['SG'])>0):
            prefix='S G '
            for c in self['SG']:
               data_str+=wrap_string(c,prefix,80,5)#80: line width, 5: label position (starting position=0)
               data_str+='\n'
  
        return data_str+'\n'

    def print_GCD1(self,NUCID):
        data_str=''
          
        name='GCD1'
        unit=Config.get_unit(name)
        value=self[name]
        if(value==''):
            return data_str

        uncertainty=self['D'+name]

        prefix=NUCID+get_prefix('gamma_com')+'$'  
        data_str+=prefix
        data_str+=print_value_in_comment(Config.get_name(name),value,uncertainty,unit)
        keyno=Config.get_keyno(name)
        if(keyno!=''):
           data_str+=' ('+keyno+')'
      
        return data_str+'\n'


    def print_GCD2(self,NUCID):
                     
        data_str=''
        name='GCD2'
        unit=Config.get_unit(name)
        value=self[name]
        if(value==''):
            return data_str
       
        uncertainty=self['D'+name]

        prefix=NUCID+get_prefix('gamma_com')+'$'  
        data_str+=prefix
        data_str+=print_value_in_comment(Config.get_name(name),value,uncertainty,unit)
        keyno=Config.get_keyno(name)
        if(keyno!=''):
           data_str+=' ('+keyno+')'
      
        return data_str+'\n'


    def print_GCD3(self,NUCID):
                     
        data_str=''
        name='GCD3'
        unit=Config.get_unit(name)
        value=self[name]
        if(value==''):
            return data_str
       
        uncertainty=self['D'+name]

        prefix=NUCID+get_prefix('gamma_com')+'$'  
        data_str+=prefix
        data_str+=print_value_in_comment(Config.get_name(name),value,uncertainty,unit)
        keyno=Config.get_keyno(name)
        if(keyno!=''):
           data_str+=' ('+keyno+')'
      
        return data_str+'\n'


    def print_GCD(self,NUCID):

        data_str=''
        count=0

        for i in range(3):
          name='GCD'+str(i+1)
          unit=Config.get_unit(name)
          value=self[name]
          if(value==''):
            continue
          
          uncertainty=self['D'+name]
 
          if(count>0):
             data_str+=', '

          count=count+1
          data_str+=print_value_in_comment(Config.get_name(name),value,uncertainty,unit)
          keyno=Config.get_keyno(name)
          if(keyno!=''):
             data_str+=' ('+keyno+')'

 
        if(data_str==''):
          return ''
        
        prefix=NUCID+get_prefix('gamma_com')

        data_str='$'+data_str
        
        data_str=wrap_string(data_str,prefix,80,5)
        data_str+='\n'

        return data_str

    #print user-defined data, it is like GCD (gamma comment data) but with more flexibity.
    def print_UDD(self,NUCID):
                     
        data_str=''
        temp_str=''

        for i in range(3):
           if(i==0):
              s=''
           else:
              s=str(i)
 
           name=self['GUDN'+s]
           unit=self['GUDU'+s]
           value=self['GUDD'+s]     
           uncertainty=self['DGUDD'+s]
          
           if(name==''):
              name='GUDN'+s

           if(value==''):
              continue
           else:
              temp_str=print_value_in_comment(name,value,uncertainty,unit)
              keyno=Config.get_keyno('GUDD'+s)
              if(keyno!=''):
                 temp_str+=' ('+keyno+')'
              
              if(data_str==''):
                 data_str=temp_str
              else:
                 data_str+=', '+temp_str

        if(data_str==''):
           return ''
 
        data_str='$'+data_str

        prefix=NUCID+get_prefix('gamma_com')
        data_str=wrap_string(data_str,prefix,80,5) 
        
        return data_str+'\n'

    def print_EM(self,NUCID):
        
        data_str=''
        #EM=gamma_EM.keys()
        EM=gamma_EM_names #sorted in order of EL, ML

        unit='' 
        temp_str=''
        

        for c in EM:
            if(c[0]=='B'):
               value=self[c]
               if(value==''):
                   continue
               else:
                   uncertainty=self['D'+c]
                   name=c
                   temp_str=print_value_in_continuation(name,value,uncertainty,'')
                   
                   if(data_str==''):
                       data_str=temp_str
                   else:
                       data_str+='$ '+temp_str

                           
        if(data_str==''):
            return ''

        prefix=NUCID+get_prefix('gamma_EM')
        data_str=wrap_string(data_str,prefix,80,5) 
            
        return data_str+'\n'


    def print_comment(self,NUCID):

        data_str=''
        temp=''

        #print document record first
        comments=self['DG']
        prefix=NUCID+get_prefix('gamma_doc')
        if comments:
           for c in comments:
               data_str+=wrap_string(c,prefix,80,5)#80: line width, 5: label position (starting position=0)
               data_str+='\n'


        comments=self['CG']
        if not comments:
            return data_str

        prefix=NUCID+get_prefix('gamma_com')
        
        #right now, this method can only handle comments,starting with 'E$', 'T$', 'J$', '$' and so on        
        for c in comments:
          V=[]
          temp=c
          temp.strip()
          while(len(temp)>0):
            pos1=temp.rfind('$') #in output file from ensdf2excel, all comments are written into one cell. So we need to split it
            pos2=temp[:pos1].rfind(' ')
            if(pos1>0 and pos2>0):
              if((pos1-pos2)>10):
                pos2=pos1

              V.append(temp[pos2:].strip())
              temp=temp[:pos2].strip()
            else:
              V.append(temp)
              break

          for i in range(len(V)):
            n=-(i+1)
            data_str+=wrap_string(V[n],prefix,80,5)#80: line width, 5: label position (starting position=0)
            data_str+='\n'

        return data_str


    def print_angular(self,NUCID):
        
        data_str=''
        names=['A2','A4','A6']
         
        unit='' 
        temp_str=''
        

        for c in names:
            value=self[c]
            
            if(value==''):
                continue
            else:
                if(value.find('-')!=0 and value.find('+')<0):
                   value='+'+value

                uncertainty=self['D'+c]
                name=c
                temp_str=print_value_in_continuation(name,value,uncertainty,'')
                if(data_str==''):
                    data_str=temp_str
                else:
                    data_str+='$ '+temp_str
                
        if(data_str==''):
            return ''

        prefix=NUCID+get_prefix('gamma_con')
        data_str=wrap_string(data_str,prefix,80,5)    
        return data_str+'\n'


    def print_DCO(self,NUCID):
        
        data_str=''
        
        name='DCO'
        unit=''
       
        value=self[name]
        if(value==''):
            return ''

        uncertainty=self['D'+name]
        data_str=print_value_in_continuation(name,value,uncertainty,'')

        prefix=NUCID+get_prefix('gamma_con')
        data_str=prefix+data_str

        return data_str+'\n'        

    def print_POL(self,NUCID):
        
        data_str=''
        
        name='POL'
        unit=''
       
        value=self[name]
        if(value==''):
            return ''

        uncertainty=self['D'+name]
        data_str=print_value_in_comment(name,value,uncertainty,'')

        prefix=NUCID+get_prefix('gamma_com')+'$'
        data_str=prefix+data_str

        return data_str+'\n' 


    def print_ECC(self,NUCID):
       
        data_str=''
        names=[s for s in ICC_fields.keys() if s[0]=='E']

        unit='' 
        temp_str=''
        

        for c in names:
            value=self[c]
            if(value==''):
                continue
            else:
                uncertainty=self['D'+c]
                name=c
                temp_str=print_value_in_continuation(name,value,uncertainty,'')
                if(data_str==''):
                    data_str=temp_str
                else:
                    data_str+='$ '+temp_str

                  
        if(data_str==''):
            return ''

        
        prefix=NUCID+get_prefix('gamma_con')
        data_str=wrap_string(data_str,prefix,80,5) 

        return data_str+'\n'
                   
    def print_gammas(self,NUCID):     
        
        data_str=''
        gammas=self['gammas']
        ngamma=len(gammas)
 
        if(ngamma<=0):
            return data_str
           
        for g in self['gamma']:
            data_str+=g.print_ENSDF(NUCID) #return string has '\n' at the end

        return data_str
#!/usr/bin/env python

# Contains all information of a level
# in ENSDF file (including decay record
# and all associated gamma records)
# Jun Chen
# Dec,2013

#Update:
# 3/18/2015:  add code in "e()" to handle levels like "1234.5+X"
# 10/28/2015: add code in "e()" to handle levels like "SN+X"
# 07/10/2017: add unit for LCD1, LCD2, ...
# 07/16/2017: add functions for getting lines in ENSDF files


class Level(dict):

    def __init__(self):

        for c in level_field_names:
            if(c in level_comment_names):
               self[c]=[]
            else:
               self[c]='' 

        #self['offset']={} #dict of offset level energies (energies for level at X,Y,Z,W,...) 
                          #eg, {'X':10,'Y':20}
                          #it is set only when there is level like '1234.2+X', '1345.3+W',...

        self['gammas']=[]
        self['feeding_gammas']=[]
        self['X']=0.0 #for offset level
        self.ndecays=0
        self.ndelays=0
        self.lines=[]


    def addGamma(self,gamma):
        self['gammas'].append(gamma)

    def es(self):
        return self[el_field_name].strip() 

    def e(self):
        e_str=self[el_field_name].strip()  
     
        if(len(e_str)>0 and e_str[0]=='(' and e_str[-1]==')'):
           e_str=e_str[1:-1]

        if not is_number(e_str):
           pos=e_str.find('+')

           if(pos<=0):
             if(e_str.lower() in letters):
                return self['X']
             else:
                return -1
           else:
             temp_str=e_str[:pos].strip()
             if not is_number(temp_str):
               temp_str=e_str[pos+1:].strip()

               if is_number(temp_str):
                  return float(temp_str)+self['X'];
               elif(temp_str.lower() in letters or temp_str.lower() in ['sn','sp']):#for level like,SN+X or X+SN
                  return self['X']
               else:
                  return -1
             else:           
               return float(temp_str)+self['X'];
        else:
           return float(e_str) 

    def de(self):

        e_str=self[el_field_name].strip()
        de_str=self[del_field_name].strip()  

        if not is_number(e_str) or not is_number(de_str):
            return -1

        V=convert_ENSDF(e_str,de_str)
        return float(V[1]) 
    
    def lines(self):
        return self.lines
    
    def lineAt(self,i):
        if(len(self.lines)>0):
            return self.lines[i]
        
        return ''

    def nlines(self):
        return len(self.lines)

###########################################################
### print functions:
### only for the excel2ensdf program
###########################################################

    def print_ENSDF(self,NUCID):
        
        data_str=''
  
        data_str+=self.print_level(NUCID)
        #print 'level',data_str
        data_str+=self.print_MOM(NUCID)
        data_str+=self.print_EM(NUCID)
        #print 'EM',data_str

        if(Config.newline):
           data_str+=self.print_LCD1(NUCID)
           data_str+=self.print_LCD2(NUCID)
           data_str+=self.print_LCD3(NUCID)
        else:
           data_str+=self.print_LCD(NUCID)
       
        data_str+=self.print_UDD(NUCID) #print user-defined data, it is like LCD (level comment data) but with more flexibity.

        data_str+=self.print_comment(NUCID)
        #print 'comment',data_str
        data_str+=self.print_decay(NUCID)


        data_str+=self.print_delay(NUCID)

        #print 'decay',data_str
        data_str+=self.print_gammas(NUCID)
        #print 'gammas',data_str

        return data_str


    def print_level(self,NUCID):
        
        data_str=''
        continuation=''
        prefix=''
        
        prefix=NUCID+get_prefix('level')
        data_str+=prefix
        V=[] 
        
        #store data entries that can not fill in their desinated spaces 
        #and are to be put in the comments instead (Util.comment_buffer)
        reset_comment_buffer()

        #energy
        value=self['EL']
        uncertainty=self['DEL']
        V=check_uncertainty(value,uncertainty)
        data_str+=fill_space(V[0],level_fields['EL'][1])
        data_str+=fill_space(V[1],level_fields['DEL'][1])

        #JPI
        data_str+=fill_space(' '+self['JPI'],level_fields['JPI'][1]) #add a whitespace to separate it from DEL field

        #half-life
        value=self['T']
        uncertainty=self['DT']
        V=check_uncertainty(value,uncertainty)
        if((self['T']=='') & (self['TU']=='') & (self['DT']=='')):
            data_str+=fill_space(' ',level_fields['T'][1]+level_fields['DT'][1])
        elif((self['T']!='') & (self['TU']!='')):
            data_str+=fill_space(V[0]+' '+self['TU'].upper(),level_fields['T'][1])
            data_str+=fill_space(V[1],level_fields['DT'][1])
        elif(self['T'].upper()=='STABLE'):
            data_str+=fill_space(V[0],level_fields['T'][1]+level_fields['DT'][1])
        else:
            data_str+=fill_space(V[0],level_fields['T'][1])
            data_str+=fill_space(V[1],level_fields['DT'][1])          
            print 'Warning: wrong half-life record: ',self['T']+' '+self['TU']+' '+self['DT']
            print '         --> the TU column could be missing in the data sheet!'
        
        #L
        value=self['L']      
        data_str+=fill_space(value,level_fields['L'][1])
       
        #S
        value=self['S']
        uncertainty=self['DS']
        V=check_uncertainty(value,uncertainty)
        data_str+=fill_space(V[0],level_fields['S'][1])
        data_str+=fill_space(V[1],level_fields['DS'][1])
 
        #XREF (for dataset of Adopted Levels)
        if(self['XREF']!=''):
            prefix=NUCID+get_prefix('level_xref')
            continuation=prefix+'XREF='+self['XREF']

        #ISPIN
        if(self['ISPIN']!=''):
            prefix=NUCID+get_prefix('level_con')
            if(continuation!=''):
                continuation+='\n'

            continuation=prefix+'ISPIN='+self['ISPIN']

        #g-factor
        value=self['GF']
        uncertainty=self['DGF']
        if(value!=''):
            prefix=NUCID+get_prefix('level_con')
            if(continuation!=''):
                continuation+='\n'
            
            continuation+=prefix+print_value_in_comment('G',value,uncertainty,'')


        #band flags and all other flags
        if(self['BAND']!=''):
            data_str+=fill_space(self['BAND'],1)
            if(self['LFLAG']!=''):
                prefix=NUCID+get_prefix('level_FLAG')
                if(continuation!=''):
                    continuation+='\n'
                continuation+=prefix+'FLAG='+self['LFLAG']+self['SEQ']
        elif(self['SEQ']!=''):
            data_str+=fill_space(self['SEQ'],1)
            if(self['LFLAG']!=''):
                prefix=NUCID+get_prefix('level_FLAG')
                if(continuation!=''):
                    continuation+='\n'
                continuation+=prefix+'FLAG='+self['LFLAG']
        else:
            if(len(self['LFLAG'])>1):
                data_str+=self['LFLAG'][0]
                prefix=NUCID+get_prefix('level_FLAG')
                if(continuation!=''):
                    continuation+='\n'
                continuation+=prefix+'FLAG='+self['LFLAG'][1:]
            else:
                data_str+=' ' if(self['LFLAG']=='') else self['LFLAG'][0]           


        #meta-stable mark, col 78-79: 'M' or 'M1' or 'M2', etc
        if(len(self['MS'])>0):
           data_str+=fill_space(self['MS'],level_fields['MS'][1]);
        else:
           data_str+='  ' #add two empty spaces for column 78 and 79 in ENSDF file

        #question mark        
        data_str+=fill_space(self['LQUE'],1)     

        if((data_str!='') & (continuation!='')):
            data_str+='\n'+continuation

        #add the data that do not fit in the space to comments to be printed later
        #in "print_comment"
        if comment_buffer:
            comments=self['CL']
            comment_buffer.extend(comments)
            self['CL']=[]
            self['CL'].extend(comment_buffer)

        #calculated lines marked with 'S'
        if(len(self['SL'])>0):
            prefix='S L '
            for c in self['SL']:
               data_str+='\n'+wrap_string(c,prefix,80,5)#80: line width, 5: label position (starting position=0)

        if(data_str.strip()==prefix.strip()):
            return ''

        return data_str+'\n'

    def print_LCD1(self,NUCID):
                     
        data_str=''
        name='LCD1'
        unit=Config.get_unit(name)
        value=self[name]
        if(value==''):
            return data_str
       
        uncertainty=self['D'+name]

        prefix=NUCID+get_prefix('level_com')+'$'  
        data_str+=prefix
        data_str+=print_value_in_comment(Config.get_name(name),value,uncertainty,unit)
        keyno=Config.get_keyno(name)
        if(keyno!=''):
           data_str+=' ('+keyno+')'
      
        return data_str+'\n'


    def print_LCD2(self,NUCID):
                     
        data_str=''
        name='LCD2'
        unit=Config.get_unit(name)
        value=self[name]
        if(value==''):
            return data_str
       
        uncertainty=self['D'+name]

        prefix=NUCID+get_prefix('level_com')+'$'  
        data_str+=prefix
        data_str+=print_value_in_comment(Config.get_name(name),value,uncertainty,unit)
        keyno=Config.get_keyno(name)
        if(keyno!=''):
           data_str+=' ('+keyno+')'
      
        return data_str+'\n'


    def print_LCD3(self,NUCID):
                     
        data_str=''
        name='LCD3'
        unit=Config.get_unit(name)
        value=self[name]
        if(value==''):
            return data_str
       
        uncertainty=self['D'+name]

        prefix=NUCID+get_prefix('level_com')+'$'  
        data_str+=prefix
        data_str+=print_value_in_comment(Config.get_name(name),value,uncertainty,unit)
        keyno=Config.get_keyno(name)
        if(keyno!=''):
           data_str+=' ('+keyno+')'
      
        return data_str+'\n'

    #print user-defined data, it is like LCD (level comment data) but with more flexibity.
    def print_UDD(self,NUCID):
                     
        data_str=''
        temp_str=''

        for i in range(3):
           if(i==0):
              s=''
           else:
              s=str(i)
 
           name=self['LUDN'+s]
           unit=self['LUDU'+s]
           value=self['LUDD'+s]     
           uncertainty=self['DLUDD'+s]
          
           if(name==''):
              name='LUDN'+s

           if(value==''):
              continue
           else:
              temp_str=print_value_in_comment(name,value,uncertainty,unit)
              keyno=Config.get_keyno('LUDD'+s)
              if(keyno!=''):
                 temp_str+=' ('+keyno+')'

              if(data_str==''):
                 data_str=temp_str
              else:
                 data_str+=', '+temp_str

        if(data_str==''):
           return ''
 
        data_str='$'+data_str

        prefix=NUCID+get_prefix('level_com')
        data_str=wrap_string(data_str,prefix,80,5) 
        
        return data_str+'\n'

    #put data in decay-record comment (decay comment data-DCD)
    def print_DCD(self,NUCID,decay_type):
        
        data_str=''
        temp_str=get_prefix('decay_com') #by default, for beta decay, =' CB '
        prefix=temp_str[:2]+decay_type+' '
        prefix=NUCID+prefix+'$' 

        for i in range(3):
          name='DCD'+str(i+1)
          unit=Config.get_unit(name)
          value=self[name]
          if(value==''):
            continue
       
          uncertainty=self['D'+name]
 
          data_str+=prefix
          data_str+=print_value_in_comment(Config.get_name(name),value,uncertainty,unit)
          keyno=Config.get_keyno(name)
          if(keyno!=''):
             data_str+=' ('+keyno+')'
          data_str+='\n'
      
        if(data_str==''):
          return ''
        
        return data_str

    #put data in (delayed)particle-record comment (delay comment data-PCD)
    def print_PCD(self,NUCID,delay_type):
        
        data_str=''
        temp_str=get_prefix('delay_com') #by default, for beta decay, =' CDP'
        prefix=temp_str[:3]+delay_type
        prefix=NUCID+prefix+'$' 

        for i in range(3):
          name='PCD'+str(i+1)
          unit=Config.get_unit(name)
          value=self[name]
          if(value==''):
            continue
       
          uncertainty=self['D'+name]
 
          data_str+=prefix
          data_str+=print_value_in_comment(Config.get_name(name),value,uncertainty,unit)
          keyno=Config.get_keyno(name)
          if(keyno!=''):
             data_str+=' ('+keyno+')'
          data_str+='\n'
      
        if(data_str==''):
          return ''
        
        return data_str


    def print_LCD(self,NUCID):

        data_str=''
        count=0

        for i in range(3):
          name='LCD'+str(i+1)
          unit=Config.get_unit(name)
          value=self[name]
          if(value==''):
            continue
          
          uncertainty=self['D'+name]
 
          if(count>0):
             data_str+=', '

          count=count+1
          data_str+=print_value_in_comment(Config.get_name(name),value,uncertainty,unit)
          keyno=Config.get_keyno(name)
          if(keyno!=''):
             data_str+=' ('+keyno+')'


        if(data_str==''):
          return ''
        
        prefix=NUCID+get_prefix('level_com') 

        data_str='$'+data_str
        data_str=wrap_string(data_str,prefix,80,5)
        data_str+='\n'

        return data_str


    def print_EM(self,NUCID):
        
        data_str=''
        #EM=level_EM.keys()
        EM=level_EM_names #sorted in order of EL, ML
        
        unit='' 
        temp_str=''
        

        for c in EM:
            if(c[0]=='B'):
               value=self[c]
               if(value==''):
                   continue
               else:
                   uncertainty=self['D'+c]
                   name=c
                   if(c[len(c)-2:].upper()=='UP'):
                     name=c[:len(c)-2]
                   temp_str=print_value_in_continuation(name,value,uncertainty,'')
                   
                   if(data_str==''):
                       data_str=temp_str
                   else:
                       data_str+='$ '+temp_str

                          
        if(data_str==''):
            return ''

        prefix=NUCID+get_prefix('level_EM')
        data_str=wrap_string(data_str,prefix,80,5) 
            
        return data_str+'\n'


    def print_MOM(self,NUCID):
        
        data_str=''
        MOM=level_MOM.keys()
        MOM.sort()
        
        unit='' 
        temp_str=''
        

        for c in MOM:
            if(c[0]=='M'):
               value=self[c]
               if(value==''):
                   continue
               else:
                   uncertainty=self['D'+c]
                   name=c
                   temp_str=print_value_in_continuation(name,value,uncertainty,'')
                   
                   if(data_str==''):
                       data_str=temp_str
                   else:
                       data_str+='$ '+temp_str

                          
        if(data_str==''):
            return ''

        prefix=NUCID+get_prefix('level_MOM')
        data_str=wrap_string(data_str,prefix,80,5) 
            
        return data_str+'\n'


    def print_comment(self,NUCID): #also print document record

        data_str=''

        #print document record first
        comments=self['DL']
        prefix=NUCID+get_prefix('level_doc')
        if comments:
           for c in comments:
               data_str+=wrap_string(c,prefix,80,5)#80: line width, 5: label position (starting position=0)
               data_str+='\n'

        comments=self['CL']
        if not comments:
            return data_str

        prefix=NUCID+get_prefix('level_com')
        
        #right now, this method can only handle comments,starting with 'E$', 'T$', 'J$', '$' and so on        
        for c in comments:
          V=[]
          temp=c
          temp.strip()
          while(len(temp)>0):
            pos1=temp.rfind('$') #in output file from ensdf2excel, all comments are written into one cell. So we need to split it
            pos2=temp[:pos1].rfind(' ')
            if(pos1>0 and pos2>0):
              if((pos1-pos2)>10):
                pos2=pos1

              V.append(temp[pos2:].strip())
              temp=temp[:pos2].strip()
            else:
              V.append(temp)
              break

          for i in range(len(V)):
            n=-(i+1)
            data_str+=wrap_string(V[n],prefix,80,5)#80: line width, 5: label position (starting position=0)
            data_str+='\n'

        return data_str


    def print_decay(self,NUCID):
        
        comment_data=''
        data_str=''
        continuation=''
        has_decay=False
        decay_type=''
        prefix=''

        #store data entries that can not fill in their desinated spaces 
        #and are to be put in the comments instead (Util.comment_buffer)
        reset_comment_buffer()

        if(self['EB']!='' or self['IB']!='' or self['IBE']!='' or self['TIE']!='' or self['IE']!=''): #beta+,beta- or EC decay
            has_decay=True
            decay_type='B' #for beta+, beta-
            if(self['IBE']!='' or self['TIE']!='' or self['IE']!=''):
                decay_type='E' # EC
            
            prefix=NUCID+'  '+decay_type

            value=self['EB']
            uncertainty=self['DEB']
            V=check_uncertainty(value,uncertainty)
            data_str=prefix+' '+fill_space(V[0],level_fields['EB'][1])
            data_str+=fill_space(V[1],level_fields['DEB'][1])    
            if(decay_type=='E'):
                value=self['IBE']
                uncertainty=self['DIBE']
                V=check_uncertainty(value,uncertainty)
                data_str+=fill_space(' '+V[0],level_fields['IBE'][1])#add a whitespace to separate it from DEB field
                data_str+=fill_space(V[1],level_fields['DIBE'][1])
            else:
                value=self['IB']
                uncertainty=self['DIB']
                V=check_uncertainty(value,uncertainty)
                data_str+=fill_space(' '+V[0],level_fields['IB'][1])#add a whitespace to separate it from DEB field
                data_str+=fill_space(V[1],level_fields['DIB'][1])  
            value=self['IE']
            uncertainty=self['DIE']
            V=check_uncertainty(value,uncertainty)       
            data_str+=fill_space(' '+V[0],level_fields['IE'][1])#add a whitespace to separate it from DIB field
            data_str+=fill_space(V[1],level_fields['DIE'][1])  

            value=self['LOGFT']
            uncertainty=self['DLOGFT']
            V=check_uncertainty(value,uncertainty) 
            data_str+=fill_space(' '+V[0],level_fields['LOGFT'][1])#add a whitespace to separate it from DIE field
            data_str+=fill_space(V[1],level_fields['DLOGFT'][1])  
        
            #blank between DLOGFT and TIE
            data_str=fill_space(data_str,level_fields['TIE'][0]-1) #self['TIE'][0]=TIE position=70 
                                                                     #(starting from 1 not 0)

            #IBE+IE for EC or B+ decay 
            value=self['TIE']
            uncertainty=self['DTIE']
            V=check_uncertainty(value,uncertainty)       
            data_str+=fill_space(V[0],level_fields['TIE'][1])
            data_str+=fill_space(V[1],level_fields['DTIE'][1])  

            #flag
            if(len(self['DFLAG'])>1):
                data_str+=self['DFLAG'][0]
                prefix=NUCID+'F '+decay_type+' '
                continuation=prefix+'FLAG='+self['DFLAG'][1:]
            else:
                data_str+=' ' if(self['DFLAG']=='') else self['DFLAG'][0] 


            #forbiddenness, col 78-79, e.g., '1U','2U'
            if(len(self['UN'])>0):
                data_str+=fill_space(self['UN'],2);
            else:
                data_str+='  ' #add two empty spaces for column 78 and 79 in ENSDF file

            #question mark
            data_str+=fill_space(self['DQUE'],1)

            if((data_str!='') & (continuation!='')):
                data_str+='\n'+continuation

        elif(self['EA']):
            has_decay=True
            decay_type='A'

            prefix=NUCID+'  '+decay_type

            value=self['EA']
            uncertainty=self['DEA']
            V=check_uncertainty(value,uncertainty)
            data_str=prefix+' '+fill_space(V[0],level_fields['EA'][1])
            data_str+=fill_space(V[1],level_fields['DEA'][1])  

            value=self['IA']
            uncertainty=self['DIA']
            V=check_uncertainty(value,uncertainty)         
            data_str+=fill_space(' '+V[0],level_fields['IA'][1])#add a whitespace to separate it from DEA field
            data_str+=fill_space(V[1],level_fields['DIA'][1])   

            value=self['HF']
            uncertainty=self['DHF']
            V=check_uncertainty(value,uncertainty)
            data_str+=fill_space(' '+V[0],level_fields['HF'][1])#add a whitespace to separate it from DIA field
            data_str+=fill_space(V[1],level_fields['DHF'][1]) 
        
            data_str=fill_space(data_str,level_fields['DFLAG'][0]-1) #self['DFLAG'][0]=alpha decay flag position=77
                                                                     #(starting from 1 not 0)
            
            #flag
            if(len(self['DFLAG'])>1):
                data_str+=self['DFLAG'][0]
                prefix=NUCID+'F '+decay_type+' '
                continuation=prefix+'FLAG='+self['DFLAG'][1:]
            else:
                data_str+=' ' if(self['DFLAG']=='') else self['DFLAG'][0] 

            #question mark
            data_str+='  ' #add one empty space for column 78-79 in ENSDF file
            data_str+=fill_space(self['DQUE'],1)

            if((data_str!='') & (continuation!='')):
                data_str+='\n'+continuation

        else:
            return ''

        #calculated lines marked with 'S'
        name='S'+decay_type
        if(len(self[name])>0):
            prefix=NUCID+'S '+decay_type+' '
            for c in self[name]:
               data_str+='\n'+wrap_string(c,prefix,80,5)#80: line width, 5: label position (starting position=0)

        #comment
        col_name='C'+decay_type

        #add the data that do not fit in the space to comments to be printed later
        if comment_buffer:
            comments=self[col_name]
            comment_buffer.extend(comments)
            self[col_name]=[]
            self[col_name].extend(comment_buffer)

        comments=self[col_name]
        if((data_str!='') & (len(comments)>0)):
            prefix=NUCID+' c'+decay_type+' '
        
            #right now, this method can only handle comments,starting with 'E$', 'IB$',and so on   
            for c in comments:     
                data_str+='\n'+wrap_string(c,prefix,80,5)#80: line width, 5: label position (starting position=0)
         
        comment_data=self.print_DCD(NUCID,decay_type)
        if(comment_data!=''):
          return data_str+'\n'+comment_data     

        return data_str+'\n'
                   

  
    def print_delay(self,NUCID):
        
        comment_data=''
        data_str=''
        continuation=''
        has_delay=False

        delay_type=''
        if(Config.delay_type!=''):
            delay_type=Config.delay_type
        elif(len(self['EDP'])>0):
            delay_type='P'
        elif(len(self['EDN'])>0):
            delay_type='N'
        elif(len(self['EDA'])>0):
            delay_type='A'

        if(delay_type==''):#if name of delayed energy column is given as 'EP', assume delayed proton 
           delay_type='P'

        prefix=NUCID+'  D'+delay_type

        #store data entries that can not fill in their desinated spaces 
        #and are to be put in the comments instead (Util.comment_buffer)
        reset_comment_buffer()
        
        name='ED'+delay_type
        name=name.strip()
        if(self[name]==''):
            name='EP'

        if(self[name]!='' or self['IP']!=''): #delayed-particle
            has_delay=True

            value=self[name]
            uncertainty=self['D'+name]
            V=check_uncertainty(value,uncertainty)
            data_str=prefix+' '+fill_space(V[0],level_fields[name][1]-1)#leave one space between prefix and EDP
            data_str+=fill_space(V[1],level_fields['D'+name][1])  
  
            value=self['IP']
            uncertainty=self['DIP']
            V=check_uncertainty(value,uncertainty)
            data_str+=fill_space(' '+V[0],level_fields['IP'][1])#add a whitespace to separate it from DEDP field
            data_str+=fill_space(V[1],level_fields['DIP'][1])  

            value=self['ED']       
            data_str+=fill_space(' '+value,level_fields['ED'][1])#add a whitespace to separate it from DIP field 

            value=self['WIDTH']
            uncertainty=self['DWIDTH']
            V=check_uncertainty(value,uncertainty) 
            data_str+=fill_space(V[0],level_fields['WIDTH'][1])
            data_str+=fill_space(V[1],level_fields['DWIDTH'][1])  
        
            value=self['LP']
            data_str+=fill_space(value,level_fields['LP'][1])  

            data_str=fill_space(data_str,level_fields['PFLAG'][0]-1) #self['PFLAG'][0]=alpha decay flag position=77
                                                                     #(starting from 1 not 0)

            #flag
            if(len(self['PFLAG'])>1):
                data_str+=self['PFLAG'][0]
                continuation=prefix+'FLAG='+self['PFLAG'][1:]
            else:
                data_str+=' ' if(self['PFLAG']=='') else self['PFLAG'][0] 


            #coincidence & question mark
            if((self['PCOIN']!='') & (self['PCOIN'].upper()=='C')):
                data_str+='C ' #column 78 and 79
            else:
                data_str+='  ' #add two empty spaces for column 78 and 79 in ENSDF file

            #question mark
            data_str+=fill_space(self['PQUE'],1)

            if((data_str!='') & (continuation!='')):
                data_str+='\n'+continuation
        else:
            return ''

        #comment
        col_name='CD'+delay_type

        #add the data that do not fit in the space to comments to be printed later
        if comment_buffer:
            comments=self[col_name]
            comment_buffer.extend(comments)
            self[col_name]=[]
            self[col_name].extend(comment_buffer)

        comments=self[col_name]
        if((data_str!='') & (len(comments)>0)):
            prefix=NUCID+' cD'+delay_type
        
            #right now, this method can only handle comments,starting with 'E$', 'IB$',and so on   
            for c in comments:     
                data_str+='\n'+wrap_string(c,prefix,80,5)#80: line width, 5: label position (starting position=0)
         
        comment_data=self.print_PCD(NUCID,delay_type)
        if(comment_data!=''):
          return data_str+'\n'+comment_data     

        return data_str+'\n'

    def print_gammas(self,NUCID):     
        
        data_str=''
        gammas=self['gammas']
        ngamma=len(gammas)
 
        if(ngamma<=0):
            return data_str
        for g in self['gammas']:
            data_str+=g.print_ENSDF(NUCID) #return string has '\n' at the end
    
        return data_str
#!/usr/bin/env python

#Update:
# 07/16/2017:  add code to assign lines for each level and gamma
# 07/25/2017:  add writing gamma feedings sheet (decaying/feeding 
#                 gammas for each level
# 08/10/2017:  impove the "get_entry_by_energy_and_nsigma()" function to find the closest match
#              fix a bug that it stopp searching for other matches when it found a match with very
#              large uncertainty, like a match 10.2E3 1, uncertainty=100 keV for 1691g from 11620(2)
#              level. The program searched up and down from 10.2E3 level and found no matches and 
#              then stopped. The fix is to continue search up and down until a maximum number of
#              non-matches is reached, and then it stops. 
 
from xlwt import * 

import os, math, string, sys


class ENSDF(object):

####
    def __init__(self):
        self.NUCID=''
        self.DSID=''
        self.levels=[]
        self.gammas=[] 
        self.unplaced_gammas=[]
        self.unplaced_decays=[]
        self.unplaced_delays=[]
        self.header=None
        self.is_good=True
        self.level_column_names=[]
        self.gamma_column_names=[]
        self.parent_column_names=[]
        self.norm_column_names=[]
        self.pn_column_names=[]
        self.Q_column_names=[]
        self.com_column_names=[]
        self.column_names=[]
        self.print_commands=['print_CC','print_EM']
        self.offset={} #for level offset, 'X', 'Y','Z','W', and so on

        self.verbose=True
####            
    def addLevel(self,level):
        self.levels.append(level)
       
  
###
    def get_entry_by_energy_and_nsigma_old(self,energy,de,entries,nsigma):

        if(len(entries)<=0 or (isinstance(entries[0],Level)==False and isinstance(entries[0],Gamma)==False)):
          return []  
    
        if(de<0):
           de=1
   
        nsearch=10        

        unc=1 # set uncertainty for entries without uncertainty
        matches=[]
        found=False
        nlevel=len(entries)
        median_i=0
        median_e=0
        median_de=-1
        left=0
        right=nlevel-1
    
        left_e=entries[left].e()
        left_de=entries[left].de()
        if(left_de<=0):
           left_de=unc

        right_e=entries[right].e()
        right_de=entries[right].de()  
        if(right_de<=0):
           right_de=unc      


        if(abs(energy-right_e)<nsigma*max(right_de,de)):
           found=True
           median_i=right
           matches.append(entries[right])
        elif(abs(left_e-energy)<nsigma*max(left_de,de)):
           found=True
           median_i=left
           matches.append(entries[left])
        elif(energy>right_e or energy<left_e):
           return []
        
        while(not found):
          median_i=int((left+right)/2)# when right=left+1, median=left
          match=entries[median_i]
          median_e =match.e()
          median_de=match.de()
          if(median_de<=0):
             median_de=unc

          if(abs(median_e-energy)<nsigma*max(median_de,de)):
             matches.append(match)
             found=True
          elif(median_e>energy):
             if(right==left):
                break
             right=median_i
             continue
          else:
             #when there is no match, right=left+1 and it will go into the infinite loop with median==int((left+right)/2)==left
             if(left==median_i and left==right-1): #actual when left==median, it has to be left==right-1. 
               left=right #it is set to make median=right to compare energy with right value, since when left=right-1, it is always median=left. 
             else:
               left=median_i
             continue
        #end while

        #When reaching here, that means match has been found, found=True 
        #It is possible that there are multiple matches
   
        #search right side of the match found above
        count=0
        index=median_i+1
        while(index<nlevel and count<=nsearch):
           match=entries[index] 
           match_e=match.e()
           match_de=match.de()
           if(match_de<=0):
             match_de=unc

           if(abs(match_e-energy)<nsigma*max(match_de,de)):
              matches.append(match)
           #else:
           #   break

           index+=1
           count+=1

        #search left side of the match found above
        count=0
        index=median_i-1
        while(index>=0 and count<=nsearch):
           match=entries[index] 
           match_e=match.e()
           match_de=match.de()
           if(match_de<=0):
             match_de=unc

           if(abs(match_e-energy)<nsigma*max(match_de,de)):
              matches.insert(0,match)             
           #else:
           #   break
           
           index-=1
           count+=1

        return matches


###
    def get_entry_by_energy_and_nsigma(self,energy,de,entries,nsigma):

        if(len(entries)<=0 or (isinstance(entries[0],Level)==False and isinstance(entries[0],Gamma)==False)):
          return []  
    
        if(de<0):
           de=1

        unc=1 # set uncertainty for entries without uncertainty
        matches=[]
        found=False
        nlevel=len(entries)
        median_i=0
        median_e=0
        median_de=-1
        left=0
        right=nlevel-1
    
        left_e=entries[left].e()
        left_de=entries[left].de()
        if(left_de<=0):
           left_de=unc

        right_e=entries[right].e()
        right_de=entries[right].de()  
        if(right_de<=0):
           right_de=unc      
         
        diff_right=abs(energy-right_e)
        diff_left=abs(energy-left_e)
        if(diff_right<nsigma*max(right_de,de)):
           found=True
           median_i=right
           matches.append(entries[right])
        elif(diff_left<nsigma*max(left_de,de)):
           found=True
           median_i=left
           matches.append(entries[left])
        elif(energy>right_e or energy<left_e):
           return []
        
        while(not found):
          median_i=int((left+right)/2)# when right=left+1, median=left
          match=entries[median_i]
          median_e =match.e()
          median_de=match.de()
          if(median_de<=0):
             median_de=unc

          if(abs(median_e-energy)<nsigma*max(median_de,de)):
             matches.append(match)
             found=True
          elif(median_e>energy):
             if(right==left):
                break
             right=median_i
             continue
          else:
             #when there is no match, right=left+1 and it will go into the infinite loop with median==int((left+right)/2)==left
             if(left==median_i and left==right-1): #actual when left==median, it has to be left==right-1. 
               left=right #it is set to make median=right to compare energy with right value, since when left=right-1, it is always median=left. 
             else:
               left=median_i
             continue
        #end while


        #When reaching here, that means match has been found, found=True 
        #It is possible that there are multiple matches
   
        #search right side of the match found above
        nskip=0
        index=median_i+1
        while(index<nlevel):
           match=entries[index] 
           match_e=match.e()
           match_de=match.de()
           if(match_de<=0):
             match_de=unc

       
           #if(abs(energy-9929)<2):
           #   print 'line 242',energy,match_e,match_de,nsigma*max(match_de,de)

           if(abs(match_e-energy)<nsigma*max(match_de,de)):
              matches.append(match)
              #if(abs(energy-9929)<2):
              #   print 'line 247',energy,de,match_e,match_de,nsigma,median_e
           else:
              nskip+=1
              if(nskip>=10 and (match_e-energy)>nsigma*de):
                 break

           index+=1

        #search left side of the match found above
        nskip=0
        index=median_i-1
        while(index>=0):
           match=entries[index] 
           match_e=match.e()
           match_de=match.de()
           if(match_de<=0):
             match_de=unc

           #if(abs(energy-9929)<2):
           #   print 'line 266',energy,match_e,match_de,nsigma*max(match_de,de)

           if(abs(match_e-energy)<nsigma*max(match_de,de)):
              matches.insert(0,match)
              #if(abs(energy-9929)<2):
              #   print 'line 271',energy,de,match_e,match_de,nsigma,median_e,found
           else:
              nskip+=1
              if(nskip>=10 and (energy-match_e)>nsigma*de):
                 break
           
           index-=1


        #debug
        #if(abs(energy-9929)<2):
        #   for l in matches:
        #      print 'line 255',energy,de,match_e,match_de,nsigma,median_e
        #      print '        ',l.e()

        return matches

###
    def get_entry_by_energy(self,energy,de,entries):
        size=0
        matched=[]
        max_nsigma=5
        for n in range(max_nsigma):
           nsigma=n+1
           matched=self.get_entry_by_energy_and_nsigma(energy,de,entries,nsigma)
           size=len(matched)
           if(size>0):
              for m in matched:
                 if(abs(m.e()-energy)<nsigma*de):#make sure we have found the right matches
                    return matched
        
        #if(size==0):
        #   print 'Warning: no match found within {0} sigmas for entry at energy={1}'.format(max_nsigma,energy)
                    
        return matched
        
####
#   get gammas matching gamma energy
    def get_gamma_by_energy(self,energy,de):
        return self.get_entry_by_energy(energy,de,self.gammas)
    
####
#   get levels matching level energy
    def get_level_by_energy(self,energy,de):
        return self.get_entry_by_energy(energy,de,self.levels)

####
#   get levels matching spin
#   input spin should be a string of integer or half-integer
#   however, int or float values are also acceptable
    def get_level_by_spin(self,spin):

        matches=[]
        spin_str=''
        wrong_spin=False
        levels=self.levels
      
        if((type(spin) is int) or (type(spin) is float)):
           if(spin!=int(spin) and 2*spin!=int(2*spin)):
              wrong_spin=True
           elif(spin==int(spin)):
              spin_str=str(int(spin))
           else:#half_integer
              spin_str=str(int(2*spin))+'/2'
        elif(type(spin) is not str):
           wrong_spin=True    
        else:
           spin_str=spin
           s=spin_str.split('/')
           if(not s[0].isdigit()):
              wrong_spin=True
              if('+' in s[0] or '-' in s[0]):
                 print 'Warning: + or - found in input spin: {0}'.format(spin)
                 print '  get_level_by_spin() search level by spin value.'
           elif(len(s)==2):
              if(s[1]!='2'):
                 wrong_spin=True
              elif(not is_odd(s[0])):
                 wrong_spin=True
           elif(len(s)>2):
              wrong_spin=True
 
        if(wrong_spin):
           print 'Warning: wrong spin value in get_level_by_spin():{0}'.format(spin)   
           return []
        
        for l in levels:
           if spin_str in l['JPI']:
              matches.append(l)

        return matches



####
#   find the final level of a gamma transition
    def find_final_level(self,gamma):
        final_level=None
        if(gamma==None or gamma['ilevel']==None or gamma['ilevel'].e()<0):
           return None

        eg=gamma.e()
        deg=gamma.de()

        if(eg<=0 or gamma.es()=='X'):
           return None

        if(deg<=0):
           deg=0.5

        ei=gamma['ilevel'].e()
        dei=gamma['ilevel'].de()
        if(dei<0):
           dei=1

        try:
          mass=float(self.NUCID[:3].strip())
        except ValueError:
          mass=100

        recoil_correction=eg*eg/(2*mass*931.5*1000);
        ef=ei-eg-recoil_correction
        de=math.sqrt(dei**2+deg**2)      


        if(ef<3*de):
           ef=0.0

        if(ef<=-1):
          return None
 
        ef_fixed=-1
        try:
         ef_fixed=float(gamma['FL'])
        except ValueError:
         ef_fixed=-1

        if(ef_fixed>=0):#gamma has "FL" record to specify the final level with exact level energy
          for l in self.levels:
             if(abs(l.e()-ef_fixed)<1E-5):
                return l
          print 'Error: FL={0} is given but no match found. Please check.'.format(ef_fixed)
          return None
           
        
        #if difference is within 5 sigma,it is considered to be the final level. For cases that 
        #there are multiple choices of final levels, the first one will be used and we leave 
        #accuracy to be checked by the ENSDF standard checking programs for now.
        matched=[]
        if(de<0.5):
           de=0.5
        matched=self.get_level_by_energy(ef,de)
        size=0
        size=len(matched)

        #debug
        #if(abs(eg-1692)<2):
        #   print '** line 289**',eg,de,size,ei,ef,de,recoil_correction
        #   print '         ',gamma['ilevel'].e(),gamma.e(),matched[0].e()
             

        if(size==0):
           if(self.verbose):
              print 'Warning: no final level found for Eg={0} from level {1}. Please check.'.format(eg,gamma['ilevel'].e())
           return None
        elif(size>1):
           minL=matched[0]
           minDE=abs(minL.e()-ef)
           for l in matched[1:]:
             if(abs(l.e()-ef)<minDE):
                minDE=abs(l.e()-ef)
                minL=l

           #debug
           #if(abs(eg-1692)<2):
           #   print '** line 306**','minL.e=',minL.e(),'minDE=',minDE,'ef=',ef

           final_level=minL
           
           if(self.verbose):
             print 'Warning: multiple possible final levels found for Eg={0} from level {1}.'.format(eg,gamma['ilevel'].e())
             print '         The closest match at {0} will be used. Please check.'.format(minL.e())
             print '         The other possible matches are:'
             for l in matched:
                if(l!=minL):
                   print '                                {0}+/-{1}'.format(l.e(),l.de())

        else:
           final_level=matched[0]
       
        return final_level


####
#   add continuation record to level or gamma
    def add_continuation(self,level_or_gamma,cont):
        record_type=''
        is_good=False

        if(isinstance(level_or_gamma,Level)):
           record_type='L'
           field_names=level_field_names
        elif(isinstance(level_or_gamma,Gamma)):
           record_type='G'
           field_names=gamma_field_names
        else:
           return

        s=cont[9:].strip()
        if(s[0]=='$'):
          s=s[1:].strip()

        i=s.find('$')
        if(i<0):
           i=len(s)
       
        while(i>0):
            temp_str=s[:i].strip()
            j=find_operator(temp_str)[0]
            op=find_operator(temp_str)[1]
            


            name=temp_str[:j].strip()
            value=temp_str[j+len(op):].strip()
            uncertainty=op

            

            if(op=='='):
               j=value.find(' ')
               uncertainty=''
               if(j>0):
                  uncertainty=value[j:].strip()
                  value=value[:j].strip()
                  if(uncertainty[:2]=='{I' or uncertainty[:2]=='{i'):#for records with lower-case format
                    uncertainty=uncertainty[2:]
                  if(uncertainty[-1]=='}'):
                    uncertainty=uncertainty[:-1]
                  if(not is_number(uncertainty)):
                     j=uncertainty.find(' ')
                     k=uncertainty.find('(')
                     if(j>0 and k>j): #0.34 5 (1994Pa24),uncertainty='5 (1994Pa24)'                   
                       uncertainty=uncertainty[:j]
                     else:
                       uncertainty=''


            is_good=True
           
            if(name not in field_names):
               is_good=False
               if(name=='FLAG'):
                 is_good=True
                 name=record_type+name
               if(name+'UP' in field_names): #for BE1,BM1,BE2,... in level continuation record
                 is_good=True
                 name=name+'UP'
               if(name=='G'): #g-factor
                 is_good=True
                 name='GF'
            elif(isinstance(level_or_gamma[name],list)):
               is_good=False

            if(not is_good):
               energy_str=level_or_gamma['E'+record_type]
               if(self.verbose):
                  print 'Warning: continuation record has conflict or unknown name: '+name+' for E'+record_type+'='+energy_str
               name=''
 
            if(name in field_names):
               if(record_type=='L'):
                 append_column_name(name,self.level_column_names)
               else:
                 append_column_name(name,self.gamma_column_names)

               if(name.find('FLAG')>=0):
                  level_or_gamma[name]=level_or_gamma[name]+value
               else:
                  level_or_gamma[name]=value


            name='D'+name
            if(name in field_names):
               if(record_type=='L'):
                 append_column_name(name,self.level_column_names)
               else:
                 append_column_name(name,self.gamma_column_names)

               level_or_gamma[name]=uncertainty  

            s=s[i+1:].strip()
            if(s==''):
               break
            i=s.find('$')               
            if(i<0):
               i=len(s)

        return

####
# return a data string with unc in bracket if available
# for a given record name
# NOTE: if record name like EL, EG is given, return
#       value(unc)
#       if unc column name is given, return unc
    def get_data_str(self,level_or_gamma,name):
        
        data_str=''
        value=''
        uncertainty=''
        is_good=False

        if(isinstance(level_or_gamma,Level) & (name in self.level_column_names)):
           is_good=True
        elif(isinstance(level_or_gamma,Gamma) & (name in self.gamma_column_names)):
           is_good=True
        else:
           return data_str
        
        if(isinstance(level_or_gamma[name],list)):
           is_good=False

        if(is_good):             
           value=level_or_gamma[name]
           name='D'+name
           if(name in all_field_names and name!='DL'):
              uncertainty=level_or_gamma[name]
           
           if(uncertainty==''):
              data_str=value 
           elif(uncertainty.isdigit()): #for sysmetirc uncertainty 
              data_str=value+'('+uncertainty+')'
           elif(uncertainty[0]=='+' or uncertainty[0]=='-'): #for asymmetric unc like +4-3
              data_str=value+'('+uncertainty+')'               
           else:
              if(uncertainty in ENSDF_op):
                 uncertainty=convert_ENSDF_op(uncertainty)
              
              if(uncertainty not in operators):
                 uncertainty=''

              data_str=uncertainty+value
           
        return data_str

####
    def get_column_names(self):

        column_names1=[]
        column_names2=[]
        column_names=[]

        temp1=[]
        temp2=[]

        mark_names=['LFLAG','LQUE','BAND',  
                    'GFLAG','GQUE',
                    'DFLAG','AFLAG','DQUE']

        
        for name in self.level_column_names:
            if((name[0]=='D') & (name[1:] in self.level_column_names)):
               continue
            
            if(name in mark_names):
               temp1.append(name)
            else:
               column_names1.append(name)
     
        self.level_column_names[:]=[]
        self.level_column_names.extend(column_names1)
        self.level_column_names.extend(temp1)

        for name in self.gamma_column_names:
            if((name[0]=='D') & (name[1:] in self.gamma_column_names)):
               continue
            
            if(name in mark_names):
               temp2.append(name)
            else:
               column_names2.append(name)

        self.gamma_column_names[:]=[]
        self.gamma_column_names.extend(column_names2)
        self.gamma_column_names.extend(temp2)

       
        column_names.extend(column_names1)
        column_names.extend(temp1)
        column_names.extend(column_names2)
        column_names.extend(temp2)


        #column_names.extend(self.level_column_names) #first item must be EL
        #column_names.extend(self.gamma_column_names) #first item must be EG
        column_names.extend(self.com_column_names)        

        self.column_names=column_names
        return column_names


    def read_ensdf_file(self,ensdf_file,verbose=True):
        lines=ensdf_file.readlines()
        return self.read_ensdf_lines(lines,verbose)
   
####
#   data block could be:
#      1,level/gamma record with the following continuation record (must be the next line)
#      2,level/gamma comments (comments are read separately from level/gamma records)
#      3,continuation record only. This happens when there are comments in between
#        level/gamma records and continuation records. In this case, gamma/level records,
#        comments, and continuation records each are read separately.

    def read_ensdf_lines(self,lines,verbose=True):

        self.verbose=verbose

        data_block=[]
        curr_type=''
        prev_type=''

        for line in lines:
            if(line.strip(' \n\r')==''):
               continue

            curr_type=line[6:8]
            if((curr_type=='PN') and (line[5]!=' ')):
               curr_type='CPN'

            if((line[5]==' ') | (curr_type!=prev_type)):
               try:
                 self.read_data_block(data_block)
               except Exception as e:
                 print 'Error when reading data block:'
                 print data_block
                 print e
                 sys.exit(0)

               data_block[:]=[]
            #print '***'
            #print line
            #print prev_type,curr_type
  
            data_block.append(line)
            prev_type=curr_type
            

        if(data_block!=[]):
            try:
              self.read_data_block(data_block) #for last data block
            except Exception as e:
              print 'Error when reading the last data block:'
              print e
              sys.exit(0)

        #print self.header.reaction,self.level_column_names, self.gamma_column_names, self.com_column_names

        self.gammas=sort_gammas(self.gammas)

        return self.get_column_names()

####
    def read_data_block(self,data_block):

        is_cont=False

        nline=len(data_block)
        if(nline==0):
           return

        #remove the heading empty lines
        while(nline>0):
              if(data_block[0].strip(' \n')!=''):
                 break
              data_block.pop(0)
              nline=len(data_block)
        
        if(nline==0):
           return

      
        #if(data_block[0][5].upper()=='S'):#skip calculated continuation record for now
        #   return
       
        if(data_block[0][5] in continuation_marks and data_block[0][6]==' '):
           is_cont=True

        data_type=data_block[0][6:8]
        
        
        is_header=False

        if(data_type not in [' L',' G',' B',' E',' A',' D']):
           is_header=True

        ###### ensdf file header and comments
        if(is_header):
           self.read_header_and_comments(data_block)
    
        ###### ensdf file data body (levels and gammas), including continuation records
        ###### but excluding comments, which are read above

        #level
        if(data_type==' L'):
           level=None
           final_level=None
           if(is_cont):
              level=self.levels.pop()
              for s in data_block:
                  if(s[5] in continuation_marks):
                     self.add_continuation(level,s)   
           else:
              level=self.make_level(data_block)  #this function will also read following continuation record if it is next line
                                                 #othersie, it will be read elsewhere
              
              energy_str=level[el_field_name].strip().upper()
              pos=energy_str.find('+')
              if(pos>0 or (energy_str.lower() in letters)): #offset level, eg, 'X','Z','W', or levels, like '123.4+X' or 'X+123.4'
                  if(pos>0):#for levels based on offset levels, eg, '123.4+X' or 'X+123.4'
                     label=energy_str[pos+1:]
                     if(len(label)>1):#for case X+123.4
                        label=energy_str[:pos]
                  else:#offset level, eg, 'X','Z','W
                     label=energy_str
                  
                  pre_e=0.0
                  if(len(label)==1 and (label.lower() in letters)):
                     if(len(self.levels)>0):
                        pre_e=self.levels[-1].e()               
                     
                     if(label not in self.offset):
                        self.offset[label]=pre_e+0.1
                        level['X']=self.offset[label]               
                     else:
                        level['X']=self.offset[label]

            
           level.lines.extend(data_block)
                 
           self.levels.append(level)
           #print '*** '+level['EL']+'   ',level.e(),' X=',level['X']
           return

        if((data_type in [' B',' E',' A']) or data_type[0:2]==' D'):  #decay or delay records for a level

           is_unplaced=False
           is_same_level=False

           if(self.levels==[]):
              is_unplaced=True
           else:
              es=self.levels[-1]['EL']
              if(es=='' or es.upper()=='UNPLACED'):
                 is_unplaced=True
              elif(self.levels[-1].ndecays>0 or self.levels[-1].ndelays>0):
                 is_same_level=True

           if(is_unplaced):#create a fake level for unplaced decays or delays
              level=Level()
           elif(is_same_level):#create a fake level for each extra decays or delays
              level=Level()
              level['EL']=self.levels[-1]['EL']
           else:
              level=self.levels.pop()          
    
           temp_level=self.make_level(data_block)#this function will also read following continuation record if it is next line
                                                 #othersie, it will be read elsewhere

           for name in level_field_names:
               if((level[name]=='') | (level[name]==[])):
                  level[name]=temp_level[name]

           if(data_type[0:2]==' D'):
              level.ndelays+=1
           else:
              level.ndecays+=1

           level.lines.extend(data_block)
           
           self.levels.append(level)

           return

        #gamma
        if(data_type==' G'):
           gamma=None

           if(is_cont):
              gamma=self.gammas.pop()
              for s in data_block:
                  if(s[5] in continuation_marks):
                     self.add_continuation(gamma,s)   
           else:
              gamma=self.make_gamma(data_block)  #this function will also read following continuation record if it is next line
                                                 #othersie, it will be read elsewhere

           gamma.lines.extend(data_block)
           
           #if(gamma['RI']=='LC='):
           #   print data_block
           is_unplaced=False
           if(self.levels==[]):
              is_unplaced=True
           else:
              es=self.levels[-1]['EL']
              if(es=='' or es.upper()=='UNPLACED'):
                 is_unplaced=True

           if(is_unplaced):
              self.unplaced_gammas.append(gamma)
           else:
              level=self.levels.pop()

              #in case, continuation record is read separately from gamma record. 
              #That case, the gamma has already been added to its parent level
              if(is_cont):  
                level['gammas'].pop()

              level['gammas'].append(gamma)
              self.levels.append(level)
              gamma['ilevel']=level    #NOTE: any change of 'gamma' after 'append(gamma)' will also apply to the gamma already appended in "level['gammas']"
                                       #it is like that they point to the same 'Gamma' object. 

              try:
                final_level=self.find_final_level(gamma)
                
                #debug
                if(abs(gamma.e()-1691)<2):
                   print '********* line 754',gamma.e(),final_level.e()

              except Exception:
                print 'Can\'t find final level for gamma: {0}! Something wrong!\n'.format(gamma['EG'])
                final_level=None
 
              gamma['flevel']=final_level

              if(final_level!=None):
                final_level['feeding_gammas'].append(gamma) #add this gamma to the feeding gammas of the final level it decays to

              #insert two columns for final levels "EF","JF"
              if(gamma['flevel']!=None):
                gamma['EF']=gamma['flevel']['EL']
                gamma['DEF']=gamma['flevel']['DEL']
                gamma['JF']=gamma['flevel']['JPI']
                index=self.gamma_column_names.index('EG')
                insert_column_name(index,'EF',self.gamma_column_names)
                if(gamma['flevel']['JPI']!=''):
                  insert_column_name(index+1,'JF',self.gamma_column_names)

              #if(gamma['flevel']!=None):
              # print 'gamma',gamma.e(),'final level',gamma['flevel'].e(),gamma['flevel'].de(),'JPI=',gamma['flevel']['JPI']
              #else:
              # print 'gamma',gamma.e(), 'has no final level'
           self.gammas.append(gamma)
              
        return


#####
#   read ensdf file header and comments
#   before calling, make sure data_block is not empty
    def read_header_and_comments(self,data_block):

        nline=len(data_block)
        data_type=data_block[0][6:8]
        
        if(data_type[1]=='D'):
           data_type=data_type+data_block[0][8:9]

        #NUCID and reaction name
        if((nline==1) & (data_type=='  ')):
           self.header=Header()
           self.header.nuclide=data_block[0][:5].strip()
           self.header.reaction=data_block[0][9:39].strip()
           #self.header.reference=data_block[0][39:65].strip(' \n')
           self.header.nsr=data_block[0][39:65].strip(' \n')

           try:
               self.NUCID=self.decode_Nuclide(self.header.nuclide.strip())
           except Exception as e:
               print 'Error when decoding nuclide name'
               print e
               sys.exit(0)

           return
        
        #reference
        if((nline>=2) & (data_block[0].find('Compiled (unevaluated) dataset from')>0)):
           if(self.header==None):
             self.header=Header()

           self.header.reference=data_block[1][9:].strip(' \n')
           return

        #compiler
        if((nline>=1) & (data_block[0].find('Compiled by')>0)):
           if(self.header==None):
             self.header=Header()

           s=get_string(data_block)
           index=s.find('Compiled by')
           index+=len('Compiled by')
           self.header.compiler=s[index:].strip(' \n')
           return

        if((data_type==' H')):
           if(self.header==None):
             self.header=Header()

           s=get_string(data_block)
           self.header.history.append(s.strip())

           index=s.find('AUT=')
           if(index>=0):
              s=s[index+4:]
              index=s.find('$')
              if(index>0):
                 s=s[:index]
              self.header.evaluators.append(s.strip())
           return
 
        #general comments
        if(data_type.upper()=='C '):
           if(self.header==None):
             self.header=Header()

           s=get_string(data_block)
           self.header.general_comments.append(s)
           return
        
   
        #level comments (document records also included)
        if(data_type.upper() in level_comment_names):
           if(self.header==None):
             self.header=Header()

           s=get_string(data_block)
           if(self.levels==[]): #general level comments
              self.header.level_comments.append(data_type.upper()+s)          
           else:                #individual level comments
              level=self.levels.pop()
              level[data_type.upper()].append(s)
              
              level.lines.extend(data_block)
              
              self.levels.append(level)
              append_column_name(data_type.upper(),self.com_column_names)
           return    
       
        #gamma comments (document records also included)
        if(data_type.upper() in gamma_comment_names):
           if(self.header==None):
             self.header=Header()

           s=get_string(data_block)
           if(self.levels==[]): 
              if(self.unplaced_gammas==[]):#general gamma comments
                 self.header.gamma_comments.append(data_type.upper()+s)
              else:                        #unplaced gamma comments
                 gamma=self.unplaced_gammas.pop()
                 gamma[data_type.upper()].append(s)
                 
                 gamma.lines.extend(data_block)
                 
                 self.unplaced_gammas.append(gamma)
                 append_column_name(data_type.upper(),self.com_column_names)
           else:                           #individual gamma comments
              level=self.levels.pop()
              gamma=level['gammas'].pop()
              gamma[data_type.upper()].append(s)
              
              gamma.lines.extend(data_block)
              
              level['gammas'].append(gamma)
              self.levels.append(level)
              append_column_name(data_type.upper(),self.com_column_names)
           return
           

        #parent record
        if(data_type.upper()==' P'):
           if(self.header==None):
             self.header=Header()
           
           self.header.parent=self.make_parent(data_block)          
           return

        #parent record comments
        if(data_type.upper()=='CP' or data_type.upper()=='DP'):
           if(self.header==None):
             return
           if(self.header.parent==None):
             return
              
           name=data_type.upper()
           if(name=='DP'):
              name='PDOC'

           s=get_string(data_block)
           self.header.parent[name].append(s)
           return

        #N record
        if(data_type.upper()==' N'):
           if(self.header==None):
             self.header=Header()
           
           self.header.norm=self.make_norm(data_block)          
           return

        #N record comments
        if(data_type.upper()=='CN' or data_type.upper()=='DN'):
           if(self.header==None):
             return
           if(self.header.norm==None):
             return
              
           name=data_type.upper()
           if(name=='DN'):
              name='NDOC'

           s=get_string(data_block)
           self.header.norm[name].append(s)
           return

        #PN record
        if(data_type.upper()=='PN' and (data_block[0][5]==' ')):
           if(self.header==None):
             self.header=Header()
           
           self.header.pn=self.make_pn(data_block)          
           return

        #PN record comments
        if((data_type.upper()=='PN') and (data_block[0][5]!=' ')):
           if(self.header==None):
             return
           if(self.header.pn==None):
             return
           
           name='CPN'
           if(data_block[0][5].upper()=='D'):
              name='PNDOC'

           s=get_string(data_block)
           self.header.pn[name].append(s)
   
           return

        #Q record
        if(data_type.upper()==' Q'):
           if(self.header==None):
             self.header=Header()
           
           self.header.Q=self.make_QRecord(data_block)          
           return

        #Q record comments
        if(data_type.upper()=='CQ' or data_type.upper()=='DQ'):
           if(self.header==None):
             return
           if(self.header.Q==None):
             return
              
           name=data_type.upper()
           #document record, but DQ field is reserved for uncertainty of Q-value, so QDOC is used instead
           if(name=='DQ'):
              name='QDOC'

           s=get_string(data_block)
           self.header.Q[name].append(s)
           return

        #XREF record (for Adopted dataset)
        if(data_type.upper()==' X'):
           if(self.header==None):
             self.header=Header()
               
           self.header.XREFs.append(data_block[0][8:].strip(' \r\n'))            
           return

        return

#####
#   make a parent level from a ENSDF-format parent record
    def make_parent(self,data_block):

        parent=Parent()
        nline=len(data_block)

        s=data_block[0]

        if(s[7]!='P'):
           return None

        for name in parent_record_names:        
            i=parent_fields[name][0]-1
            j=i+parent_fields[name][1]

            if(name=='TPU'):
               continue

            parent[name]=s[i:j].strip()
            if(parent[name]!=''):
               append_column_name(name,self.parent_column_names)
               if(name=='TP'):
                  j=parent[name].find(' ')
                  if(j>0):
                     parent['TPU']=parent[name][j:].strip()
                     parent[name]=parent[name][:j].strip()
                     append_column_name('TPU',self.parent_column_names)              

        if(nline==1):
           return parent

                                      
        return parent


#####
#   make N fields from a ENSDF-format N record
    def make_norm(self,data_block):

        norm=NRecord()
        nline=len(data_block)

        s=data_block[0]

        if(s[7]!='N'):
           return None

        for name in norm_record_names:
            i=norm_fields[name][0]-1
            j=i+norm_fields[name][1]  

            norm[name]=s[i:j].strip()
            if(norm[name]!=''):
               append_column_name(name,self.norm_column_names)

        if(nline==1):
           return norm
                                      
        return norm


#####
#   make PN fields from a ENSDF-format PN record
    def make_pn(self,data_block):

        pn=PNRecord()
        nline=len(data_block)

        s=data_block[0]

        if((s[6]!='P') or (s[7]!='N')):
           return None

        for name in pn_record_names:
            i=pn_fields[name][0]-1
            j=i+pn_fields[name][1]  

            pn[name]=s[i:j].strip()
            if(pn[name]!=''):
               append_column_name(name,self.pn_column_names)

        if(nline==1):
           return pn
                                      
        return pn

#####
#   make Q fields from a ENSDF-format Q record
    def make_QRecord(self,data_block):

        Q=QRecord()
        nline=len(data_block)

        s=data_block[0]

        if(s[7]!='Q'):
           return None

        for name in Q_record_names:
            i=Q_fields[name][0]-1
            j=i+Q_fields[name][1]  

            Q[name]=s[i:j].strip()
            if(Q[name]!=''):
               append_column_name(name,self.Q_column_names)

        if(nline==1):
           return Q
                                      
        return Q

#####
#   make a level from a ENSDF-format level record, including continuation record
    def make_level(self,data_block):

        level=Level()
        nline=len(data_block)

        s=data_block[0]

        if(s[7]=='L'):
           names=level_record_names
        elif(s[7]=='B'):
           names=beta_record_names
        elif(s[7]=='E'):
           names=ec_record_names
        elif(s[7]=='A'):
           names=alpha_record_names
        elif(s[7]=='D'):
           names=delay_record_names
        else:
           return None

        for name in names:        
            i=level_fields[name][0]-1
            j=i+level_fields[name][1]
            if(level_fields[name][1]==-1): #for FLAG and QUE marks
               j=i+1
            if(name=='TU'):
               continue

            level[name]=s[i:j].strip()
            if(level[name]!=''):
               append_column_name(name,self.level_column_names)
               if(name=='T'):
                  j=level[name].find(' ')
                  if(j>0):
                     level['TU']=level[name][j:].strip()
                     level[name]=level[name][:j].strip()
                     append_column_name('TU',self.level_column_names)             

        if(nline==1):
           return level

        for s in data_block[1:]:
          try:
            if(s[5] in continuation_marks):
               self.add_continuation(level,s)
            elif(s[5]=='S'):#calculated lines
               name='S'+s[7]
               level[name].append(get_string([s]))
          except Exception:
               print 'Error: in add_continuation() in make_level(): '+s

        return level

####
#   make a gamma from a ENSDF-format level record, including continuation record
    def make_gamma(self,data_block):
        gamma=Gamma()
        nline=len(data_block)

        s=data_block[0]

        if(s[7]!='G'):
           return None


        for name in gamma_record_names:
            i=gamma_fields[name][0]-1
            j=i+gamma_fields[name][1]  
            if(gamma_fields[name][1]==-1): #for FLAG and QUE marks
               j=i+1

            gamma[name]=s[i:j].strip()
            if(gamma[name]!=''):
               append_column_name(name,self.gamma_column_names)

        if(nline==1):
           return gamma

        for s in data_block[1:]:
            if(s[5] in continuation_marks):
               self.add_continuation(gamma,s)
            elif(s[5]=='S'):
               gamma['SG'].append(get_string([s]))
                                      
        return gamma
    

################################################################################
#   write
################################################################################

####
    def write_header_sheet(self,book,sheet_name):

        header_sheet=book.add_sheet(sheet_name);
        style=easyxf('alignment: horizontal left,vert center;')
 
        header=self.header
        
        if (header==None):
            print 'Error when writing header sheet: null header!'
            sys.exit(0)

        #print 'maxrow',maxrow,'maxcol',maxcol    

        # Cell Types: 0=Empty, 1=Text, 2=Number, 3=Date, 4=Boolean, 5=Error, 6=Blank
        #if (maxrow != 6): error_Header()

        has_nucleus=0
        has_reaction=0
        has_gcom=0       #flag for general comment
        has_compiler=0
        has_nsr=0
        has_reference=0
        has_level_com=0
        has_gamma_com=0
       
        k=0;

        if (header.nuclide != ''):
            has_nucleus=1
        header_sheet.write(k,0,"NUCLIDE",style);
        header_sheet.write(k,1,header.nuclide,style);      
        k+=1

        if (header.reaction != ''):
            has_reaction=1
        header_sheet.write(k,0,"REACTION",style);
        header_sheet.write(k,1,header.reaction,style);      
        k+=1

        if (header.nsr != ''):
            has_nsr=1
        header_sheet.write(k,0,"NSR",style);
        header_sheet.write(k,1,header.nsr,style);      
        k+=1

        if (header.reference != ''):
            has_reference=1
        header_sheet.write(k,0,"REFERENCE",style);
        header_sheet.write(k,1,header.reference,style);      
        k+=1

        if (header.compiler != ''):
            has_compiler=1
        header_sheet.write(k,0,"COMPILER",style);
        header_sheet.write(k,1,header.compiler,style);      
        k+=1

        if (header.general_comments != []):
            has_gcom=1
            for s in header.general_comments:
              header_sheet.write(k,0,"COMMENT",style);
              header_sheet.write(k,1,s);      
              k+=1

        if (header.level_comments != []):
            has_level_com=1
            for s in header.level_comments:
              index=2
              if(s[1]=='D'):#for delayed-particle
                index=3
              header_sheet.write(k,0,s[0:index],style);
              header_sheet.write(k,1,s[index:],style);      
              k+=1
       
        if (header.gamma_comments != []):
            has_gamma_com=1
            for s in header.gamma_comments:
              header_sheet.write(k,0,s[0:2],style);
              header_sheet.write(k,1,s[2:],style);      
              k+=1
       
        #write parent record
        if (header.parent!=None):
            for name in self.parent_column_names: #exclude comments, treated separately
                if(isinstance(header.parent[name],list)):
                   continue
                 
                header_sheet.write(k,0,name,style)
                header_sheet.write(k,1,header.parent[name],style)
                k+=1

            #write parent comments
            for name in ['CP','PDOC']:
               if (header.parent[name] != []):
                   for s in header.parent[name]:
                     header_sheet.write(k,0,name,style);
                     header_sheet.write(k,1,s,style);      
                     k+=1         

        #write N record
        if (header.norm!=None):
            for name in self.norm_column_names: #exclude comments, treated separately
                if(isinstance(header.norm[name],list)):
                   continue

                header_sheet.write(k,0,name,style)
                header_sheet.write(k,1,header.norm[name],style)
                k+=1

            #write N comments
            for name in ['CN','NDOC']:
               if (header.norm[name] != []):
                   for s in header.norm[name]:
                     header_sheet.write(k,0,name,style);
                     header_sheet.write(k,1,s,style);      
                     k+=1    

        #write PN record
        if (header.pn!=None):
            for name in self.pn_column_names: #exclude comments, treated separately
                if(isinstance(header.pn[name],list)):
                   continue

                header_sheet.write(k,0,name,style)
                header_sheet.write(k,1,header.pn[name],style)
                k+=1

            #write PN comments
            for name in ['CPN','PNDOC']:
               if (header.pn[name] != []):
                   for s in header.pn[name]:
                     header_sheet.write(k,0,name,style);
                     header_sheet.write(k,1,s,style);      
                     k+=1  


        #write Q record
        if (header.Q!=None):
            for name in self.Q_column_names: #exclude comments, treated separately
                if(isinstance(header.Q[name],list)):
                   continue

                header_sheet.write(k,0,name,style)
                header_sheet.write(k,1,header.Q[name],style)
                k+=1

            #write Q comments
            for name in ['CQ','QDOC']:
               if (header.Q[name] != []):
                   for s in header.Q[name]:
                     header_sheet.write(k,0,name,style);
                     header_sheet.write(k,1,s,style);      
                     k+=1 


        #if(has_nucleus==0 | has_reaction==0 | has_gcom==0 | has_compiler==0):
        #    f=error_Header()

        #write delay type
        n=header.reaction.find('DECAY')
        if (n>0):
            temp=header.reaction[0:n]
            delay_type=''
            if(temp.find('ECP')>0 or temp.find('B+P')>0):
               delay_type='P'
            elif(temp.find('B-N')>0 or temp.find('B-2N')>0):
               delay_type='N'
            elif(temp.find('ECA')>0 or temp.find('B+A')>0):
               delay_type='A'
            
            if(len(delay_type)>0):
               header_sheet.write(k,0,'DELAY_TYPE',style)
               header_sheet.write(k,1,delay_type,style)
               k+=1

        return

####  
    def write_data_sheet(self,book,sheet_name):   

        data_sheet=book.add_sheet(sheet_name,cell_overwrite_ok=True);

        style=easyxf('alignment: horizontal left,vert center;')
        style_bgr=easyxf('alignment: horizontal left,vert center; pattern: pattern solid, fore_colour light_green;')

        style_border=easyxf('alignment: horizontal left,vert center; font: bold on; borders: top thin')
        style_bold=easyxf('alignment: horizontal left,vert center; font: colour red, bold on; borders: top thin')
        style_bold_bgr=easyxf('alignment: horizontal left,vert center; font: colour red, bold on; borders: top thin; pattern: pattern solid, fore_colour light_green;')


 
        ncol=0
        nrow=0

        for ncol,name in enumerate(self.column_names):
            data_sheet.write(nrow,ncol,name,style)


        unplaced_gammas=self.unplaced_gammas
        for g in unplaced_gammas:
            nrow+=1
            for name in self.gamma_column_names:
                if(isinstance(g[name],list)):
                   continue

                ncol=self.column_names.index(name)

                data_sheet.write(nrow,ncol,self.get_data_str(g,name),style)

            #write comment, right now all comments for the same record are written in one string
            for name in self.com_column_names:
                if(name!="CG"):
                   continue


                ncol=self.column_names.index(name)
                comments=''
                for s in g[name]:
                    if(comments==''):
                       comments=s.strip()
                    else:
                       comments+=' '+s.strip()
                data_sheet.write(nrow,ncol,comments,style)
                
        
        levels=self.levels

        for l in levels:
            nrow+=1
            
            #write level records
            for name in self.level_column_names: #exclude comments and gammas, treated separately

                if(isinstance(l[name],list)):
                   continue


                ncol=self.column_names.index(name)
                data_sheet.write(nrow,ncol,self.get_data_str(l,name),style)

            #write comments
            for name in self.com_column_names:
                if name not in level_comment_names:
                   continue

                ncol=self.column_names.index(name)
                comments=''
                for s in l[name]:
                    if(comments==''):
                       comments=s.strip()
                    else:
                       comments+=' '+s.strip()

                data_sheet.write(nrow,ncol,comments,style)

            if(l['gammas']!=[]):
               nrow-=1
 
            #write gammas
            for g in l['gammas']:
                nrow+=1

                for name in self.gamma_column_names:
                    if(isinstance(g[name],list)):
                       continue

                    ncol=self.column_names.index(name)
                     
                    #set background
                    if(name=='EG'):
                        data_sheet.write(nrow,ncol,"",style_bgr)

                    if((name=='EG' or name=='RI') and l['gammas'].index(g)==0):
                        data_sheet.write(nrow,ncol,self.get_data_str(g,name),style_bold_bgr)
                    elif(l['gammas'].index(g)==0):
                        data_sheet.write(nrow,ncol,self.get_data_str(g,name),style_border)
                    elif(name=='EG' or name=='RI'):
                        data_sheet.write(nrow,ncol,self.get_data_str(g,name),style_bgr)
                    else:
                        data_sheet.write(nrow,ncol,self.get_data_str(g,name),style)

                #write comments
                for name in self.com_column_names:
                    if(name not in gamma_comment_names):
                       continue

                    ncol=self.column_names.index(name)
                    comments=''
                    for s in g[name]:
                        if(comments==''):
                           comments=s.strip()
                        else:
                           comments+=' '+s.strip()
                    data_sheet.write(nrow,ncol,comments,style)

        data_sheet.set_panes_frozen(True) # frozen headings instead of split panes
        data_sheet.set_horz_split_pos(1) # in general, freeze after last heading row      
        return         


####  
#   write the intensity matrix: 
#   first row: final levels from low to high
#   first col: intial levels from high to low
    def write_intensity_sheet(self,book,sheet_name):   

        data_sheet=book.add_sheet(sheet_name,cell_overwrite_ok=True);

        style=easyxf('alignment: horizontal left,vert center;')
        style_bgr=easyxf('alignment: horizontal left,vert center; pattern: pattern solid, fore_colour light_green;')
        style_border=easyxf('alignment: horizontal left,vert center; font: bold on; borders: top thin')
        style_bold_border=easyxf('alignment: horizontal left,vert center; font: colour red, bold on; borders: top thin')
        style_bold=easyxf('alignment: horizontal left,vert center; font: colour red, bold on')
        style_bold_bgr=easyxf('alignment: horizontal left,vert center; font: colour red, bold on; pattern: pattern solid, fore_colour light_green;')    

        levels=self.levels #levels is already sorted from low to high

        ilevels=[]#initial levels, from high to low
        flevels=[]#final levels, from low to high
        
        i=0
        nlevels=len(levels)  
   
        for i in range(nlevels):
            n=nlevels-1-i
            l=levels[n]
            if(l['gammas']!=[]):
               ilevels.append(l)

        for i in range(nlevels):
            fl=levels[i]
            is_final_level=False
            for j in range(i+1,nlevels):
               il=levels[j]
               for g in il['gammas']:
                  if(g['flevel']!=None and g['flevel'].es()==fl.es()):
                     is_final_level=True
                     break

               if(is_final_level):
                  break
            
            if(is_final_level):
               flevels.append(fl)
        
        if(ilevels==[] or flevels==[]):
           return


        #set background
        for i in range(len(ilevels)):
          nrow=i+2
          for j in range(len(flevels)+2):
              ncol=j
              if(nrow%2==1):
                  data_sheet.write(nrow,ncol,"",style_bgr)

        #entry in the first row starts from the third col
        #entry in the first col starts from the third row

        #write first and second row
        nrow=0
        for i in range(len(flevels)):
           ncol=i+2
           data_sheet.write(nrow,ncol,flevels[i].es(),style_bold_border)#level energy
           data_sheet.write(nrow+1,ncol,flevels[i]['JPI'],style_bold_border)#JPI

        #write first and second col
        ncol=0
        for i in range(len(ilevels)):
           nrow=i+2
 
           if(nrow%2==1):
              data_sheet.write(nrow,ncol,ilevels[i].es(),style_bold_bgr)
              data_sheet.write(nrow,ncol+1,ilevels[i]['JPI'],style_bold_bgr)
           else:
              data_sheet.write(nrow,ncol,ilevels[i].es(),style_bold)
              data_sheet.write(nrow,ncol+1,ilevels[i]['JPI'],style_bold)


        nilevels=len(ilevels)
        nrow=1
        for i in range(nilevels):
           il=ilevels[i]
           nrow+=1

           for g in il['gammas']:
              if(g['flevel']==None):
                 continue

              ncol=flevels.index(g['flevel'])+2

              if(ncol<0):
                 print 'Something wrong when writing intensity matrix!'
                 return
               
              RI=g['RI']
              DRI=g['DRI']
              if(g.dri()>0):
                RI+='('+DRI+')'
              elif(len(DRI)>0):
                RI=DRI+' '+RI

              if(nrow%2==1):
                  data_sheet.write(nrow,ncol,RI,style_bgr)
              else:
                  data_sheet.write(nrow,ncol,RI,style)

        data_sheet.set_panes_frozen(True) # frozen headings instead of split panes
        data_sheet.set_horz_split_pos(2) # in general, freeze after last heading row      
        return

####  
#   write gamma feedings scheme (feeding and fed levels): 
    def write_feedings_sheet(self,book,sheet_name):   

        data_sheet=book.add_sheet(sheet_name,cell_overwrite_ok=True);

        style=easyxf('alignment: horizontal left,vert center;')
        style_bgr=easyxf('alignment: horizontal left,vert center; pattern: pattern solid, fore_colour light_green;')

        style_border=easyxf('alignment: horizontal left,vert center; font: bold on; borders: top thin')
        style_bold=easyxf('alignment: horizontal left,vert center; font: colour red, bold on; borders: top thin')
        style_bold_bgr=easyxf('alignment: horizontal left,vert center; font: colour red, bold on; borders: top thin; pattern: pattern solid, fore_colour light_green;')


        #style=easyxf('alignment: horizontal left,vert center;')
        #style_bgr=easyxf('alignment: horizontal left,vert center; pattern: pattern solid, fore_colour light_green;')
        #style_border=easyxf('alignment: horizontal left,vert center; font: bold on; borders: top thin')
        #style_bold_border=easyxf('alignment: horizontal left,vert center; font: colour red, bold on; borders: top thin')
        #style_bold=easyxf('alignment: horizontal left,vert center; font: colour red, bold on')
        #style_bold_bgr=easyxf('alignment: horizontal left,vert center; font: colour red, bold on; pattern: pattern solid, fore_colour light_green;')    

        levels=self.levels #levels is already sorted from low to high

        ncol=0
        nrow=0
        level_column_names=['EL','JPI','T','TU']
        decaying_gamma_column_names=['EG','RI','MUL','EF','JF']
        feeding_gamma_column_names=['EG','RI','MUL','EI','JI']

        column_names=[]
        column_names.extend(level_column_names)
        column_names.extend(decaying_gamma_column_names)
        column_names.extend(feeding_gamma_column_names)

        column_titles=['EL','JPI','T','TU','DECAY EG','RI','MUL','TO LEVEL','JF','Feeding EG','RI','MUL','FROM LEVEL','JF']
        for ncol,title in enumerate(column_titles):
            data_sheet.write(nrow,ncol,title,style)


        for l in levels:
            nrow+=1
            
            #write level records
            for name in level_column_names:

                if(isinstance(l[name],list)):
                   continue


                ncol=column_names.index(name)
                data_sheet.write(nrow,ncol,self.get_data_str(l,name),style)


            offset=len(level_column_names)

            temp_nrow=nrow
            if(l['gammas']!=[]):
               nrow-=1
                

            #write decaying gammas
            gammas=l['gammas']
            for g in gammas:
                nrow+=1

                for name in decaying_gamma_column_names:
                    if(isinstance(g[name],list)):
                       continue

                    ncol=decaying_gamma_column_names.index(name)+offset
                     
                    #set background
                    if(name=='EG'):
                        data_sheet.write(nrow,ncol,"",style_bgr)

                    if((name=='EG' or name=='RI') and gammas.index(g)==0):
                        data_sheet.write(nrow,ncol,self.get_data_str(g,name),style_bold_bgr)
                    elif(gammas.index(g)==0):
                        data_sheet.write(nrow,ncol,self.get_data_str(g,name),style_border)
                    elif(name=='EG' or name=='RI'):
                        data_sheet.write(nrow,ncol,self.get_data_str(g,name),style_bgr)
                    else:
                        data_sheet.write(nrow,ncol,self.get_data_str(g,name),style)
            
            max_nrow1=nrow
            offset=len(level_column_names)+len(decaying_gamma_column_names)

            nrow=temp_nrow
            if(l['feeding_gammas']!=[]):
               nrow-=1
         
            #write feeding gammas
            gammas=l['feeding_gammas']
            for g in gammas:
                nrow+=1

                for name in feeding_gamma_column_names:
                    if(isinstance(g[name],list)):
                       continue

                    ncol=feeding_gamma_column_names.index(name)+offset
                     
                    #set background
                    if(name=='EG'):
                        data_sheet.write(nrow,ncol,"",style_bgr)

                    if(name=='EI'):
                        if(gammas.index(g)==0):
                           data_sheet.write(nrow,ncol,self.get_data_str(g['ilevel'],'EL'),style_border)
                        else:
                           data_sheet.write(nrow,ncol,self.get_data_str(g['ilevel'],'EL'),style)
                    elif(name=='JI'):
                        if(gammas.index(g)==0):
                           data_sheet.write(nrow,ncol,self.get_data_str(g['ilevel'],'JPI'),style_border)
                        else:
                           data_sheet.write(nrow,ncol,self.get_data_str(g['ilevel'],'JPI'),style)
                    elif((name=='EG' or name=='RI') and gammas.index(g)==0):
                        data_sheet.write(nrow,ncol,self.get_data_str(g,name),style_bold_bgr)
                    elif(gammas.index(g)==0):
                        data_sheet.write(nrow,ncol,self.get_data_str(g,name),style_border)
                    elif(name=='EG' or name=='RI'):
                        data_sheet.write(nrow,ncol,self.get_data_str(g,name),style_bgr)
                    else:
                        data_sheet.write(nrow,ncol,self.get_data_str(g,name),style)

            max_nrow2=nrow

            #set bgr for empty cells
            if(max_nrow2<max_nrow1 or l['feeding_gammas']==[]):
                offset=len(level_column_names)+len(decaying_gamma_column_names)
                start=max_nrow2+1
                nrow=max_nrow1
                if(l['feeding_gammas']==[]):
                    start=temp_nrow
                for r in range(start,max_nrow1+1):
                    for name in feeding_gamma_column_names:
                        ncol=feeding_gamma_column_names.index(name)+offset
                        if((name=='EG' or name=='RI') and r==temp_nrow):
                           data_sheet.write(r,ncol,"",style_bold_bgr)
                        elif(name=='EG' or name=='RI'):
                           data_sheet.write(r,ncol,"",style_bgr)
                        elif(r==temp_nrow):
                           data_sheet.write(r,ncol,"",style_border)

            if(max_nrow2>max_nrow1 or l['gammas']==[]):
                offset=len(level_column_names)
                start=max_nrow1+1
                nrow=max_nrow2
                if(l['gammas']==[]):
                    start=temp_nrow
                for r in range(start,max_nrow2+1):
                    for name in decaying_gamma_column_names:
                        ncol=decaying_gamma_column_names.index(name)+offset
                        if((name=='EG' or name=='RI') and r==temp_nrow):
                           data_sheet.write(r,ncol,"",style_bold_bgr)
                        elif(name=='EG' or name=='RI'):
                           data_sheet.write(r,ncol,"",style_bgr)
                        elif(r==temp_nrow):
                           data_sheet.write(r,ncol,"",style_border)
         
                   
        data_sheet.set_panes_frozen(True) # frozen headings instead of split panes
        data_sheet.set_horz_split_pos(1) # in general, freeze after last heading row      
        return         

####  
    def write_data_sheet_by_gamma(self,book,sheet_name):   

        data_sheet=book.add_sheet(sheet_name);
        style=easyxf('alignment: horizontal left,vert center;')
 
        #gammas is already sorted by order of gamma energies
        #self.gammas=sort_gammas(gammas)

        levels_written=[]
       
        nrow=0

        for ncol,name in enumerate(self.column_names):
            data_sheet.write(nrow,ncol,name,style)


        gammas=self.gammas
        for g in gammas:
            nrow+=1

            for name in self.gamma_column_names:
                if(isinstance(g[name],list)):
                   continue

                ncol=self.column_names.index(name)
                data_sheet.write(nrow,ncol,self.get_data_str(g,name),style)
                #print '****'+name+' '+self.get_data_str(g,name)

            #write comment
            for name in self.com_column_names:
                if(name not in gamma_comment_names):
                   continue


                ncol=self.column_names.index(name)
                comments=''
                for s in g[name]:
                    if(comments==''):
                       comments=s.strip()
                    else:
                       comments+=' '+s.strip()
                data_sheet.write(nrow,ncol,comments,style)
          
            #write the level associated with this gamma                    
            level=g['ilevel']   
            if(level==None):  #unplaced gammas
               name='EL'
               ncol=self.column_names.index(name)
               data_sheet.write(nrow,ncol,'unplaced',style)               
               continue
         
            if(level in levels_written): #level properties have been aleady written in other gammas from the same level
               name='EL'
               ncol=self.column_names.index(name)
               data_sheet.write(nrow,ncol,self.get_data_str(level,name),style)               

               name='JPI'
               if(name in self.column_names):               
                  ncol=self.column_names.index(name)
                  data_sheet.write(nrow,ncol,self.get_data_str(level,name),style)

               name='XREF'
               if(name in self.column_names):               
                  ncol=self.column_names.index(name)
                  data_sheet.write(nrow,ncol,self.get_data_str(level,name),style)

               continue

            levels_written.append(level)

            for name in self.level_column_names:
                if(isinstance(level[name],list)):
                   continue

                ncol=self.column_names.index(name)
                data_sheet.write(nrow,ncol,self.get_data_str(level,name),style)

            #write comments
            for name in self.com_column_names:
                if name not in level_comment_names:
                   continue

                ncol=self.column_names.index(name)
                comments=''
                for s in level[name]:
                    if(comments==''):
                       comments=s.strip()
                    else:
                       comments+=' '+s.strip()
                data_sheet.write(nrow,ncol,comments,style)

        #write levels that don't have any gamma rays
        levels=self.levels
        for l in levels:
            if(l in levels_written):
               continue

            nrow+=1
            for name in self.level_column_names:
                if(isinstance(l[name],list)):
                   continue

                ncol=self.column_names.index(name)
                data_sheet.write(nrow,ncol,self.get_data_str(l,name),style)

            #write comments
            for name in self.com_column_names:
                if name not in level_comment_names:
                   continue

                ncol=self.column_names.index(name)
                comments=''
                for s in l[name]:
                    if(comments==''):
                       comments=s.strip()
                    else:
                       comments+=' '+s.strip()
                data_sheet.write(nrow,ncol,comments,style)


        data_sheet.set_panes_frozen(True) # frozen headings instead of split panes
        data_sheet.set_horz_split_pos(1) # in general, freeze after last heading row      
        return         

      
####  
    @staticmethod
    def decode_Nuclide(Value):
         
        Value=Value.strip()

        length=len(Value)
        i=0
        for i in range(length):
            if(Value[i].isalpha()):
                break
        
        nalphas=length-i
        ndigits=i
        correct = (length>1 & length<6)
        correct = correct & (nalphas>0 & nalphas<3) 
        correct = correct & (ndigits>0 & ndigits<4)

        correct = correct & Value[:i].isdigit() & Value[i:].isalpha()

        if(length==0):
           raise Exception("nuclide name is empty!")
        if (not correct):
           s="wrong nuclide name in header:{0}!".format(Value)
           raise Exception(s)

        Nuclide='{0:>3s}{1:<2s}'.format(Value[:i],Value[i:])
 
        return Nuclide 
	
####  
#   option: "XUNDL" or "ENSDF"
    def write_header(self,out,option):

        header=self.header
        NUCID=self.NUCID

	empty = ' '
        if(get_COMMENT_CASE()=='lower'):
          c1 = 'c'
	  c2 = '2c'
          d1 = 'd'
        else:
          c1 = 'C'
	  c2 = '2C'
          d1 = 'D'

        header_name=''
        header_value=''
        comments=[]
        ensdf_line=''
        ensdf_header='' 
     
        k = 30 - len(header.reaction)

	ensdf_line = NUCID + 4*empty + header.reaction + k*empty+ header.nsr.upper()+'\n'
        ensdf_header += ensdf_line

        #ensdf_line = NUCID + empty + c1 + 2*empty + text + header.nsr + ':'+'\n'
        #ensdf_header += ensdf_line
        #ensdf_line = NUCID + c2 + 2*empty + header.reference+'\n'
        #ensdf_header += ensdf_line

        #write history records
        prefix= NUCID + get_prefix('history')
        if(len(header.history)>0):
          for c in header.history:
             ensdf_header+=wrap_string(c,prefix,80,5)#80: line width, 5: label position (starting position=0)
             ensdf_header+='\n'
        
        #write Q-record and comments (for Adopted dataset)
        prefix= NUCID + get_prefix('Q')
        if(header.Q):
          ensdf_header+=header.Q.print_ENSDF(NUCID)

        #write XREF (for Adopted dataset)
        prefix= NUCID + get_prefix('xref')
        if(len(header.XREFs)>0):
          for c in header.XREFs:
             ensdf_header+=wrap_string(c,prefix,80,5)#80: line width, 5: label position (starting position=0)
             ensdf_header+='\n'

        #write reference (only for XUNDL file)
        prefix = NUCID + get_prefix('general_com')
        text = 'Compiled (unevaluated) dataset from '
        text += header.nsr + ':'+80*empty+header.reference
        if(len(header.reference.strip())>0 and option=='XUNDL'):
           ensdf_header += wrap_string(text,prefix,80,5)
           ensdf_header +='\n'
   
        #write compiler (only for XUNDL file)
        text = 'Compiled by '
        if(len(header.compiler.strip())>0 and option=='XUNDL'):
           ensdf_header += wrap_string(text+header.compiler,prefix,80,5)#80: line width, 5: label position (starting position=0)
           ensdf_header +='\n'

       
        #write general comments 
        comments=header.general_comments
        if comments:
          for c in comments:
             ensdf_header+=wrap_string(c,prefix,80,5)#80: line width, 5: label position (starting position=0)
             ensdf_header+='\n'

        #write general and flaged gamma and level comments (document records included)
        comments=header.gamma_comments
        comments.extend(header.level_comments)

        if comments:
          for c in comments:
             header_name=c[:2]  #comment type, read from the header in Excel file and stored in the first two elements
             header_value=c[2:] #comment body
             if(header_name.upper()[0]=='D'):
                prefix = NUCID + empty + d1 + header_name[1] + empty
             else:
                prefix = NUCID + empty + c1 + header_name[1] + empty
             ensdf_header+=wrap_string(header_value,prefix,80,5)#80: line width, 5: label position (starting position=0)
             ensdf_header+='\n'

        #write parent record and comments (decay dataset), norm record and comments, and PN record and comments
        if(header.parent!=None):
             parent_NUCID=header.parent['PID']
             ensdf_header+=header.parent.print_ENSDF(parent_NUCID)
        if(header.norm!=None):
             ensdf_header+=header.norm.print_ENSDF(NUCID)
        if(header.pn!=None):
             ensdf_header+=header.pn.print_ENSDF(NUCID)
       
        out.write(ensdf_header)
        #print ensdf_header[i]

	return

####
    def print_data(command):
        if(command not in self.print_commands):
           return

        pass
####  
    def write_data(self,out):
        self.write_band(out)
        self.write_unplaced_gammas(out)
        self.write_levels(out)
        return

####
    def write_band(self,out):
        pass

####
    def write_unplaced_gammas(self,out):
        unplaced_gammas=self.unplaced_gammas
        for g in unplaced_gammas:
            out.write(g.print_ENSDF(self.NUCID))
        
        return


####
    def write_levels(self,out):
        levels=self.levels
        for l in levels:
            out.write(l.print_ENSDF(self.NUCID))


        return

    
####  
#   option: "XUNDL" or "ENSDF": slightly different header
    def write_ENSDF(self,out,option):
        print 'Writing header in ENSDF file...'
        self.write_header(out,option)
        print 'OK'

        print 'Writing data in ENSDF file...'
        self.write_data(out)
        print 'OK'    

####  	
    def error_Header():
	
	print 'Wrong Header Sheet. Allowed names are: '
	print '             Nuclide   (char *5)'
	print '             Reaction  (char *30)' 
	print '             NSR       (char *8) ' 
	print '             Reference (char umnlimited)'
	print '             Comment   (char unlimited) '
	print '             Compiler  (char unlimited) '
	sys.exit(0)

	return

#A program to read an ENSDF-format file and write the data and comments
#into an excel file
#Jun Chen
#April,2014
#Last Update: January 2015

#!/usr/bin/env python

from xlwt import *

import os, math, string, sys

  
def intro():

	print ' '
	print ' '
	print '         Convert ENSDF to EXCEL      '
	print '          J. Chen - June 2017  '
	print ' '
	print ' '

	return

def main():
    intro() 
    i=-1
    j=0
    filedir=''
    command=''
    ntries=0

    while i == -1:
	ens_filename=get_inputfilename("ENSDF")
        ens_filename.strip()
        j=ens_filename.find(' ')
        command=''
        if(j>0):
           command=ens_filename[j:].strip()
           ens_filename=ens_filename[:j].strip()
	i=check_filename(ens_filename) 
        ntries+=1
        if(ntries>5):
            print 'Please check if the file exists!'
            exit(0)

    print "Open file",ens_filename

    filedir=os.path.split(ens_filename)[0]
    book = Workbook()  
    xls_filename="output.xls"

    try:
        ensdf=ENSDF()

        ensdf_file=open(ens_filename,'r')

        print '\n----------------------------------------------------------'
        print 'Reading ENSDF file...'
        ensdf.read_ensdf_file(ensdf_file) 

        ensdf_file.close()

        #print ensdf.levels[0].lines
        
        if(command==''):      
           print 'Writing header sheet...'
           ensdf.write_header_sheet(book,"Header")
           print 'OK'

           print 'Writing data sheet...'
           ensdf.write_data_sheet(book,"Data")
           print 'OK'

           print 'Writing data sheet by gamma...'
           ensdf.write_data_sheet_by_gamma(book,"Data_by_gamma")
           print 'OK'

           print 'Writing intensity matrix sheet...'
           ensdf.write_intensity_sheet(book,"Intensity_Matrix")
           print 'OK'

           print 'Writing gamma feedings sheet...'
           ensdf.write_feedings_sheet(book,"Gamma_Feedings")
           print 'OK'

           filedir=filedir.strip()
           if(filedir!=''):
              filedir=filedir+'/'

           filepath=filedir+xls_filename
           book.save(filepath)
           print 'Data have been successfully written into:\n{0}'.format(filepath)
           print '----------------------------------------------------------'
        else:
           if(command in ensdf.print_commands):
              ensdf.print_data(command)

    except Exception as e:
        print 'Exception:'
        print e
        #pass

  
if __name__=="__main__":
   main()
