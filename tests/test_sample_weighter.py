'''
Script holding functions needed to test SampleWeighter class
'''
import os
from importlib.resources import files

import yaml
import numpy
import pytest
import matplotlib.pyplot as plt
import pandas            as pnd
from dmu.logging.log_store    import LogStore
from rx_misid.sample_weighter import SampleWeighter

log=LogStore.add_logger('rx_misid:test_weighter')
# -------------------------------------------------------
class Data:
    '''
    Data class
    '''
    out_dir  = '/tmp/tests/rx_misid/sample_weighter'
    nentries = 100_000

    l_block = [
        1,
        2,
        3,
        4,
        5,
        6,
        7,
        8]
# -------------------------------------------------------
@pytest.fixture(scope='session', autouse=True)
def _initialize():
    LogStore.set_level('rx_misid:weighter', 10)
    os.makedirs(Data.out_dir, exist_ok=True)
# -------------------------------------------------------
def _validate_weights(
        sample : str,
        df     : pnd.DataFrame,
        mode   : str,
        lep    : str) -> None:

    arr_pt = df[f'{lep}_TRACK_PT' ].to_numpy()
    arr_et = df[f'{lep}_TRACK_ETA'].to_numpy()
    arr_wt = df['weight'          ].to_numpy()

    arr_zr = arr_wt[arr_wt < 1e-6]
    nzeros = len(arr_zr)
    log.info(f'Zeroes= {nzeros}')

    _, (ax1, ax2, ax3) = plt.subplots(ncols=3, figsize=(20, 7))

    ax1.hist2d(arr_et, arr_pt, bins=50, cmap='viridis', vmin=0, vmax=60)
    ax1.set_xlabel(r'$\eta$')
    ax1.set_ylabel(r'$p_T$')
    ax1.set_title('Unweighted')

    ax2.hist2d(arr_et, arr_pt, bins=50, cmap='viridis', vmin=0, vmax=None, weights=arr_wt)
    ax2.set_xlabel(r'$\eta$')
    ax2.set_ylabel(r'$p_T$')
    ax2.set_title('Weighted')

    if sample in ['Bu_JpsiK_ee_eq_DPC', 'Bu_Kee_eq_btosllball05_DPC', 'DATA_24_MagUp_24c2']:
        rng = 0, 2.00
        bins= 3
    else:
        rng = 0, 0.01
        bins= 200

    ax3.hist(arr_wt, bins=bins, range=rng)
    ax3.set_xlabel('Weights')

    plt.tight_layout()
    plt.savefig(f'{Data.out_dir}/{mode}_{sample}_{lep}.png')
    plt.close()
# -------------------------------------------------------
def _get_config() -> dict:
    cfg_path = files('rx_misid_data').joinpath('misid.yaml')
    cfg_path = str(cfg_path)
    log.info(f'Picking up config from: {cfg_path}')
    with open(cfg_path, encoding='utf-8') as ifile:
        cfg = yaml.safe_load(ifile)

    return cfg['weights']
# ----------------------------
def _get_dataframe() -> pnd.DataFrame:
    df           = pnd.DataFrame(index=range(Data.nentries))
    df['hadron'] = numpy.random.choice(['kaon' ,   'pion'], size=Data.nentries)
    df['bmeson'] = numpy.random.choice(['bplus', 'bminus'], size=Data.nentries)
    df['kind'  ] = numpy.random.choice(['PassFail', 'FailPass', 'FailFail'], size=Data.nentries)
    df['block' ] = numpy.random.choice(Data.l_block, size=Data.nentries)
    df['weight'] = numpy.random.choice([1, 10], size=Data.nentries)

    df['L1_PROBNN_E'] = numpy.random.random(size=Data.nentries)
    df['L2_PROBNN_E'] = numpy.random.random(size=Data.nentries)
    df['L1_PID_E'   ] = numpy.random.uniform(-10, 10, size=Data.nentries)
    df['L2_PID_E'   ] = numpy.random.uniform(-10, 10, size=Data.nentries)

    for lep in ['L1', 'L2']:
        df[f'{lep}_TRACK_PT' ] = numpy.random.uniform(550, 20_000, Data.nentries)
        df[f'{lep}_TRACK_ETA'] = numpy.random.uniform(1.6, 4.0, Data.nentries)

    df = df[ df['L1_TRACK_PT'] < (30_000 - 5_000 * df['L1_TRACK_ETA']) ]
    df = df[ df['L2_TRACK_PT'] < (30_000 - 5_000 * df['L2_TRACK_ETA']) ]

    df = df[ df['L1_TRACK_PT'] > ( 8_000 - 2_000 * df['L1_TRACK_ETA']) ]
    df = df[ df['L2_TRACK_PT'] > ( 8_000 - 2_000 * df['L2_TRACK_ETA']) ]

    return df
# ----------------------------
@pytest.mark.parametrize('sample', [
    'DATA_24_MagUp_24c2',
    'Bu_JpsiK_ee_eq_DPC',
    'Bu_Kee_eq_btosllball05_DPC',
    'Bu_piplpimnKpl_eq_sqDalitz_DPC'])
@pytest.mark.parametrize('is_sig', [True, False])
def test_simple(is_sig : bool, sample : str):
    '''
    Simplest test
    '''
    cfg = _get_config()
    df  = _get_dataframe()

    wgt = SampleWeighter(
            df    = df,
            cfg   = cfg,
            sample= sample,
            is_sig= is_sig)

    df  = wgt.get_weighted_data()

    mode = {True : 'signal', False : 'control'}[is_sig]

    _validate_weights(df=df, mode=mode, sample=sample, lep='L1')
    _validate_weights(df=df, mode=mode, sample=sample, lep='L2')
# ----------------------------
