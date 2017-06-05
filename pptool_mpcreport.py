#!/usr/bin/env python

""" PPTOOL_MPCREPORT - produce a file for submission of asteroid astrometry
                       to the Minor Planet center
    v1.0: 2017-05-25, michael.mommert@nau.edu
"""
from __future__ import print_function

import argparse
from astropy.time import Time
from astropy import units as u
from astropy.coordinates import SkyCoord

### pipeline-specific modules
import _pp_conf
from catalog import *
import toolbox

# only import if Python3 is used
if sys.version_info > (3,0):
    from builtins import str

# setup logging
logging.basicConfig(filename = _pp_conf.log_filename,
                    level    = _pp_conf.log_level,
                    format   = _pp_conf.log_formatline,
                    datefmt  = _pp_conf.log_datefmt)


def encode_number_desig(filename):
    """ read targetname from filename (provided by Horizons) and produce
        number and packed designation according to MPC guidelines """

    number = '     '
    desig = None

    filename = filename.replace('photometry_', '').replace('.dat', '')
    
    print('processing', filename)
    
    for i, line in enumerate(filename.split('_')):
        if '(' in line and ')' in filename.split('_')[i+1]:
            desig = " ".join(filename.split('_')[i:i+2])[1:-1]
        elif line.isdigit():
            number = ("%05d" % int(float(line)))

    # encode number
    try:
        if float(number[:-4]) > 25:
            number = (chr(65+(int(float(number[:-4]))-10+6)) +
                      number[-4:])
        elif float(number[:-4]) > 10:
            number = (chr(65+(int(float(number[:-4]))-10)) +
                      number[-4:])
    except ValueError:
        pass
        
    # encode designation
    yr = desig.split()[0]
    yr = {'19':'J', '20':'K'}[yr[:2]] + yr[2:]

    des = desig.split()[1]
    if len(des) > 4:
        if float(des[2:-2]) <= 25: 
            des = des[0] + chr(65+(int(float(des[2:-2]))-10+6)) + des[1]
        elif float(des[2:-2]) > 10: 
            des = des[0] + chr(65+(int(float(des[2:-2]))-10)) + des[1]
    else:
        if len(des) > 2:
            des = des[0] + ('{:02d}'.format(int(float(des[2:])))) + des[1]
            
    desig = yr + des
    
    return number, desig





if __name__ == '__main__':

    # command line arguments
    parser = argparse.ArgumentParser(description='prepare MPC submission')
    parser.add_argument('photometryfiles',
                        help='photometry files to process', nargs='+')

    args = parser.parse_args()
    filenames = args.photometryfiles

    outf = open('mpc_astrometry.dat', 'w')

    # for each photometry file, open file, read one fits file name and
    # derive telescope keyword
    for filename in filenames:

        fitsfilename = open(filename, 'r').readlines()[1].split()[0]
        fitsfilename = fitsfilename.replace('.ldac', '.fits')

        # read telescope and filter information from fits headers
        instrument = None
        hdulist = fits.open(fitsfilename, ignore_missing_end=True,
                            verify='silentfix')
        header = hdulist[0].header
        instrument = hdulist[0].header['TEL_KEYW']
            
        if instrument is None == 0:
            raise KeyError('cannot identify telescope/instrument; '
                           'please update '
                           '_pp_conf.instrument_keys accordingly')


        # assign telescope parameters (telescopes.py)
        obsparam = _pp_conf.telescope_parameters[instrument]

        # extract packed number and designation from photometry file name
        number, desig = encode_number_desig(filename)

        observatory_code = obsparam['observatory_code']

        # loop over photometry file
        for obs in open(filename, 'r').readlines():
            if '#' in obs:
                continue

            obs = obs.split()
            
            # convert observation midtime
            date = Time(float(obs[1]), format='jd', scale='utc').to_datetime()
            date = '{0:4d} {1:02d} {2:09.6f}'.format(date.year, date.month,
                                            date.day+(date.hour/24 +
                                                      date.minute/1440 +
                                                      date.second/86400))

            filtername = obs[-3]
            if filtername == '-':
                filtername = 'C'

            pos = SkyCoord(ra=float(obs[4])*u.degree,
                           dec=float(obs[5])*u.degree, frame='icrs')
            ra = pos.ra.hms
            dec = pos.dec.signed_dms

            mag = float(obs[2])
            
            outf.write((' {0:5s}'.format(number)) +
                       ('{0:7s}'.format(desig)) +
                       (' ') + # not a discovery
                       (' ') + # no note1
                       ('C') + # note2: CCD observation
                       ('{0:17s}'.format(date)) +
                       ('{0:02d} {1:02d} {2:06.3f}'.format(int(ra.h),
                                                           int(ra.m),
                                                           ra.s)) +
                       ('{0:+03d} {1:02d} {2:05.2f}'.format(int(dec.sign*dec.d),
                                                            int(dec.m),
                                                            dec.s)) +
                       ('         ') + # blank
                       ('{0:5.2f}{1:1s}'.format(mag, filtername)) +
                       ('      ') + # blank
                       ('{0:3s}'.format(observatory_code)) +
                       ('\n'))


    outf.close()
                       
                
        
