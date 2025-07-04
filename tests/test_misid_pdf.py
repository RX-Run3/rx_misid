'''
Script containing functions meant to test MisID_PDF class
'''
import os
from typing import cast

import matplotlib.pyplot as plt
import pandas            as pnd
import pytest
import zfit
from zfit.core.data         import Data       as zdata
from zfit.core.basepdf      import BasePDF    as zpdf

from dmu.stats.zfit_plotter import ZFitPlotter
from dmu.logging.log_store  import LogStore
from dmu.stats.fitter       import Fitter
from rx_misid.misid_pdf     import MisIdPdf

log=LogStore.add_logger('rx_misid:test_misid_pdf')
# ----------------------------
class Data:
    '''
    Data class
    '''
    minx    = 4500
    maxx    = 7060
    nbins   = 80

    obs_name= 'B_M_brem_track_2'
    obs     = zfit.Space(obs_name, limits=(minx, maxx))
    out_dir = '/tmp/tests/rx_misid/misid_pdf'
# -------------------------------------------------------
@pytest.fixture(scope='session', autouse=True)
def _initialize():
    LogStore.set_level('rx_misid:test_misid_pdf', 10)
    LogStore.set_level('rx_misid:misid_pdf'     , 10)
    LogStore.set_level('rx_misid:mc_scaler'     , 10)

    LogStore.set_level('rx_data:rdf_getter'     , 30)
    LogStore.set_level('rx_data:path_splitter'  , 30)

    os.makedirs(Data.out_dir, exist_ok=True)
# ----------------------------
def _plot_data(df : pnd.DataFrame, q2bin : str, name : str) -> None:
    ax = None
    for sample, df_sample in df.groupby('sample'):
        ax = df_sample[Data.obs_name].plot.hist(column=Data.obs_name, range=[Data.minx, Data.maxx], bins=Data.nbins, histtype='step', weights=df_sample['weight'], label=sample, ax=ax)

    out_dir = f'{Data.out_dir}/{name}'
    os.makedirs(out_dir, exist_ok=True)

    plt.legend()
    plt.title(f'$q^2$ bin: {q2bin}')
    plt.xlabel(r'M$(B^+)$MeV${}/c^2$')
    plt.savefig(f'{out_dir}/{q2bin}.png')
    plt.close()
# ----------------------------
def _plot_pdf(pdf  : zpdf,
              dat  : zdata,
              name : str,
              q2bin: str) -> None:

    obj   = ZFitPlotter(data=dat, model=pdf)
    obj.plot(nbins=Data.nbins)
    obj.axs[0].set_title(f'$q^2$ bin: {q2bin}')
    obj.axs[0].axvline(x=5280, color='red', linewidth=1)
    obj.axs[0].axhline(y=+0, color='gray', linestyle=':')
    obj.axs[1].axhline(y=-3, color='red' , linestyle=':')
    obj.axs[1].axhline(y=+3, color='red' , linestyle=':')
    obj.axs[1].set_ylim(-5, 5)

    out_dir = f'{Data.out_dir}/{name}'
    os.makedirs(out_dir, exist_ok=True)

    plt.savefig(f'{out_dir}/{q2bin}.png')
    plt.close()
# ----------------------------
@pytest.mark.parametrize('q2bin', ['low', 'central', 'high'])
def test_minimal_pass_fail(q2bin : str):
    '''
    Tests PDF creation only, needed for benchmarking
    '''

    obj = MisIdPdf(obs=Data.obs, q2bin=q2bin)
    obj.get_pdf(from_fits=False)
# ----------------------------
@pytest.mark.parametrize('q2bin', ['low', 'central', 'high'])
def test_minimal_mc(q2bin : str):
    '''
    Tests PDF creation from fits to MC
    '''

    obj = MisIdPdf(obs=Data.obs, q2bin=q2bin)
    obj.get_pdf(from_fits=True)
# ----------------------------
@pytest.mark.parametrize('q2bin', ['low', 'central', 'high'])
def test_pdf(q2bin : str):
    '''
    Tests PDF provided by tool
    '''

    obj = MisIdPdf(obs=Data.obs, q2bin=q2bin)
    pdf = obj.get_pdf()

    assert pdf.is_extended

    dat = obj.get_data(kind='zfit')
    dat = cast(zdata, dat)

    _plot_pdf(pdf, dat, name='test_pdf', q2bin=q2bin)
# ----------------------------
@pytest.mark.parametrize('q2bin', ['low', 'central', 'high'])
def test_data(q2bin : str):
    '''
    Tests that the tool can provide data
    '''

    obj = MisIdPdf(obs=Data.obs, q2bin=q2bin)
    df  = obj.get_data(kind='pandas')
    df  = cast(pnd.DataFrame, df)

    _plot_data(df, q2bin, name='test_data')
# ----------------------------
@pytest.mark.parametrize('q2bin', ['low', 'central', 'high'])
def test_fit(q2bin : str):
    '''
    Test fitting with PDF
    '''
    obj = MisIdPdf(obs=Data.obs, q2bin=q2bin)
    mid = obj.get_pdf()

    lam = zfit.Parameter('c', -0.001, -0.01, 0)
    nbk = zfit.Parameter('nbkg', 1000, 0, 10_000)
    exp = zfit.pdf.Exponential(obs=Data.obs, lam=lam)
    exp = exp.create_extended(nbk)

    pdf = zfit.pdf.SumPDF([mid, exp])
    dat = pdf.create_sampler()

    obj = Fitter(pdf, dat)
    obj.fit()

    _plot_pdf(pdf=pdf, dat=dat, name='test_fit', q2bin=q2bin)
# ----------------------------
@pytest.mark.parametrize('q2bin', ['low', 'central', 'high'])
def test_pdf_benchmark(benchmark, q2bin : str):
    '''
    Check how long it takes to load PDF
    '''

    def _retrieve_pdf():
        obj = MisIdPdf(obs=Data.obs, q2bin=q2bin)
        return obj.get_pdf()

    pdf = benchmark(_retrieve_pdf)

    assert pdf is not None
# ----------------------------
