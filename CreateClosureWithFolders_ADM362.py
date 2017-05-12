import pandas as pd
from numpy import math
import datetime
import calendar
from dateutil.relativedelta import relativedelta
from time import strptime
import argparse

#derives the day from derived_day, if it is missing, get the latest possible day
def getDay(day, derived_day, month, year):
    if (day == '*'):
        if not math.isnan((derived_day)):
            return int(derived_day)
        else:
            return calendar.monthrange(year, month)[1]
    return day

d = getDay('*', 30, 12, 1982)
assert d==30
d = getDay('*', float('nan'), 12, 1982)
assert d==31
  
#derives the month from the derived month, if it is missing,get December
def getMonth(month, derived_month):
    if (month == '*'):
        if (type(derived_month) is str):
            return strptime(derived_month,'%B').tm_mon
        else:
            return 12
    return strptime(month,'%B').tm_mon
 
m = getMonth('*', 'December')
assert m==12
m = getMonth('*', float('nan'))
assert m==12
m = getMonth('May', float('nan'))
assert m==5

#gets the year if the derived_year is populated, otherwise error
def getYear(year, derived_year):
    if (year == '*'):
        if not math.isnan(derived_year):
            return int(derived_year)
        else:
            #raise ValueError('Can not derive year')
            return -1
    else:    
        return int(year)
 
y = getYear('*', float('NaN'))
assert y==-1

y = getYear('*', 1925)
assert y==1925

y = getYear('1926',  float('NaN'))
assert y==1926

def getDate(day, month, year ):
    return datetime.datetime.strptime(str(day) + ' ' + str(month) + ' ' + str(year), "%d %m %Y")   
   

#gets the date from birth_date and derived_date
def getCompleteDateForRow(v):
    day = v['birth_date_day']
    month = v['birth_date_month']
    year = v['birth_date_year']
    
    if pd.isnull(day) or pd.isnull(month) or pd.isnull(year):
        return None
        
    derived_day = v['derived_date_of_birth_day']
    derived_month = v['derived_date_of_birth_month']
    derived_year = v['derived_date_of_birth_year']
                       
    calculated_year = getYear(year, derived_year)
    if (calculated_year == -1):
        return 'unknown year'
    calculated_month = getMonth(month,derived_month)
    calculated_day = getDay(day, derived_day, calculated_month, calculated_year)
    date = getDate(calculated_day, calculated_month, calculated_year)
    return date
            


#if birth date is less than 100 years, it's closed_until
#if i cannot derive birth date, it's unknown_status (must be completed manually by archivists)
def CreateClosure(v):
    birthday = v['date_of_birth']
     
    if pd.isnull(birthday):
        return 'unknown(empty)'
    
    if isinstance(birthday, datetime.date):
        new_date = birthday + relativedelta(years=100)
        if (new_date < datetime.datetime.now()):
            return('open_on_transfer')
        else:
            return('closed_until' )
    else:
        return('unknown status')


def getFolderOrFile(v):
    file_path = v['file_path']
    if pd.isnull(file_path):
        return 'error'
    if (file_path.endswith('/')):
        return 'folder'
    else:
        return 'file'



#if it's a folder, I must copy the closure_status from the files - if at least one file is open, the folder is also open
def getClosureForFolder(v):
    file_path = v['file_path']
    folder = v['folder']
    if (folder=='folder'):
        s1 = df.loc[df['file_path'].str.startswith(file_path) & df['closure_type'].str.startswith('open_on_transfer')]
        if (s1.empty):
            #check if I have closed_until or unknown_status
            s2 = df.loc[df['file_path'].str.startswith(file_path) & df['closure_type'].str.startswith('closed_until')]
            if (s2.empty):
                return 'unknown_status'
            else:
                return 'closed_until'
        else:
            return 'open_on_transfer'
    else:
        return v['closure_type']



#closure start date is equal to birth date only for closed records, for open ones we don't populate it
#for folders with only closed files, the closure start date will be the latest start date of the files
def populateClosureStartDate(v):
    from datetime import datetime
    dateOfBirth = v['date_of_birth']
    file_path = v['file_path']
    closure_type = v['closure_type']
    if (closure_type=='closed_until'):
        if (pd.isnull(dateOfBirth)):
            #if I don't have a date of birth, I must copy the latest date of birth from the files
            latestDate = df.loc[df['file_path'].str.startswith(file_path)]['date_of_birth'].sort_values(ascending=False).iloc[0]
            return (datetime.strftime(latestDate, '%Y-%m-%d %H:%M:%S'))
        else:   
            return str(datetime.strftime(dateOfBirth, '%Y-%m-%d %H:%M:%S'))




def populateClosurePeriod(v):
    closure_type = v['closure_type']
    if (closure_type=='closed_until'):
        return '100'

def populateFoiExemptionCode(v):
    closure_type = v['closure_type']
    if (closure_type=='closed_until'):
        return '41'

def populateFoiExemptionAsserted(v):
    closure_type = v['closure_type']
    if (closure_type=='closed_until'):
        return '2013'

def populateOpeningDate(v):
    return v['record_opening_date']


def process_args() :
	cliParser=argparse.ArgumentParser();
	cliParser.add_argument("transcription",help="full path of the transcription file", nargs='?');
	cliParser.add_argument("tech_acq",help="full path of the tech_acq file", nargs='?');
	cliParser.add_argument("closure_file",help="full path of the output file", nargs='?');
	
	cliArgs=cliParser.parse_args();
	return cliArgs.transcription, cliArgs.tech_acq, cliArgs.closure_file



transcription_file, tech_acq_file, output_file = process_args();
#input data, maybe give it a param?
#df1 = pd.read_csv('/home/ldamian/gitlab/fixup/transcription_metadata_v1_ADM362Y14B001.csv')
#df2 = pd.read_csv('/home/ldamian/gitlab/fixup/tech_acq_metadata_v1_ADM362Y14B001.csv')

df1 = pd.read_csv(transcription_file)
df2 = pd.read_csv(tech_acq_file)

df = pd.merge(df1, df2, on='file_path', how='outer')
df['date_of_birth'] = df.apply(getCompleteDateForRow,axis=1)
df['closure_type']=df.apply(CreateClosure, axis=1)        
df['folder'] = df.apply(getFolderOrFile,axis=1)    
df['closure_type'] = df.apply(getClosureForFolder,axis=1)
df['closure_start_date'] = df.apply(populateClosureStartDate,axis=1)        
df['closure_period'] = df.apply(populateClosurePeriod,axis=1)    
df['foi_exemption_code'] = df.apply(populateFoiExemptionCode,axis=1)    
df['foi_exemption_asserted'] = df.apply(populateFoiExemptionAsserted,axis=1)  
df['description_public']='TRUE'
df['description_alternate']=''
df['opening_date']=df.apply(populateOpeningDate,axis=1)

newcols = {
    'file_path': 'identifier', 
}
df.rename(columns=newcols, inplace=True)
    
df3 = df[['identifier','closure_start_date', 'folder', 'closure_period', 'foi_exemption_code', 'foi_exemption_asserted','description_public','description_alternate','closure_type','opening_date']]
df3.sort_values(by='identifier', inplace=True)
    
#df3.to_csv('/tmp/closure_v8_ADM362Y14S001.csv', sep=',', encoding='utf-8', index=False)
df3.to_csv(output_file, sep=',', encoding='utf-8', index=False)	





