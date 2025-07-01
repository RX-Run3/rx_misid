'''
Module with functions meant to test SampleSplitter class
'''
import os
from importlib.resources import files

import yaml
import pytest
import mplhep
import matplotlib.pyplot as plt
import pandas as pnd
from dmu.logging.log_store import LogStore
from rx_data.rdf_getter    import RDFGetter
from rx_misid.splitter     import SampleSplitter

log=LogStore.add_logger('rx_misid:test_splitter')
# -------------------------------------------------------
class Data:
    '''
    Data class
    '''
    l_hadron_id = ['kaon', 'pion']
    plt.style.use(mplhep.style.LHCb2)

    out_dir = '/tmp/tests/rx_misid/sample_splitter'
# -------------------------------------------------------
@pytest.fixture(scope='session', autouse=True)
def _initialize():
    LogStore.set_level('rx_misid:test_splitter', 10)
    LogStore.set_level('rx_misid:splitter'     , 10)
    LogStore.set_level('rx_data:rdf_getter'    , 30)
    LogStore.set_level('rx_data:path_splitter' , 30)

    os.makedirs(Data.out_dir, exist_ok=True)
# -------------------------------------------------------
def _get_config() -> dict:
    cfg_path = files('rx_misid_data').joinpath('misid.yaml')
    cfg_path = str(cfg_path)

    log.info(f'Picking up config from: {cfg_path}')
    with open(cfg_path, encoding='utf-8') as ifile:
        cfg = yaml.safe_load(ifile)

    return cfg['splitting']
# -------------------------------------------------------
def _get_rdf():
    gtr = RDFGetter(sample='DATA_24_MagUp_24c2', trigger='Hlt2RD_BuToKpEE_MVA_ext')
    rdf = gtr.get_rdf()
    uid = gtr.get_uid()
    rdf.uid = uid

    return rdf
# -------------------------------------------------------
def _check_stats(df : pnd.DataFrame):
    fail = False
    log.info(40 * '-')
    log.info(f'{"Kind":<20}{"Entries":<20}')
    log.info(40 * '-')
    for kind, df_kind in df.groupby('kind'):
        if len(df_kind) == 0:
            log.warning(f'Empty sample: {kind}')
            fail=True
            continue

        nentries = len(df_kind)

        log.info(f'{kind:<20}{nentries:<20}')
    log.info(40 * '-')

    assert not fail
# -------------------------------------------------------
def _plot_pide(df : pnd.DataFrame, hadron_id : str, is_bplus : bool) -> None:
    for kind, df_kind in df.groupby('kind'):
        ax = None
        ax = df_kind.plot.scatter(x='L1_PID_E', y='L1_PROBNN_E', color='blue', s=1, label='$e_{SS}$', ax=ax)
        ax = df_kind.plot.scatter(x='L2_PID_E', y='L2_PROBNN_E', color='red' , s=1, label='$e_{OS}$', ax=ax)

        plot_path = f'{Data.out_dir}/{hadron_id}_{is_bplus}_{kind}.png'

        ax.set_xlabel(r'$\Delta LL (e)$')
        ax.set_ylabel('ProbNN(e)')

        bname = '$B^+$' if is_bplus else '$B^-$'
        plt.title(f'{hadron_id}; {bname}; {kind}')
        plt.savefig(plot_path)
        plt.close()
# -------------------------------------------------------
@pytest.mark.parametrize('hadron_id', Data.l_hadron_id)
@pytest.mark.parametrize('is_bplus' ,    [True, False])
def test_simple(hadron_id : str, is_bplus : bool):
    '''
    Tests simplest splitting
    '''
    log.info('')
    rdf   = _get_rdf()
    cfg   = _get_config()

    spl   = SampleSplitter(rdf=rdf, hadron_id=hadron_id, is_bplus=is_bplus, cfg=cfg)
    df    = spl.get_samples()

    _check_stats(df=df)
    _plot_pide(df=df, hadron_id=hadron_id, is_bplus=is_bplus)
# -------------------------------------------------------
