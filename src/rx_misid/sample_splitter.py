'''
Module holding SampleSplitter class
'''

import pandas as pnd
from ROOT                   import RDataFrame

from dmu.rdataframe         import utilities as ut
from dmu.logging.log_store  import LogStore
from dmu.workflow.cache     import Cache     as Wcache

log=LogStore.add_logger('rx_misid:sample_splitter')
# --------------------------------
class SampleSplitter(Wcache):
    '''
    Class meant to split a dataframe into PassFail, FailPass and FailFail samples
    based on a configuration
    '''
    # --------------------------------
    def __init__(
            self,
            rdf      : RDataFrame,
            sample   : str,
            hadron_id: str,
            is_bplus : bool,
            cfg      : dict):
        '''
        rdf     : Input dataframe with data to split, It should have attached a `uid` attribute, the unique identifier
        sample  : Sample name, e.g. DATA_24_..., needed for output naming
        is_bplus: True if the sam ple that will be returned will contain B+ mesons, false for B-
        cfg     : Dictionary with configuration specifying how to split the samples
        '''
        super().__init__(
                out_path = f'sample_splitter_{sample}_{hadron_id}_{is_bplus}',
                args     = [rdf.uid, hadron_id, is_bplus, cfg])

        self._b_id     = 521
        self._sample   = sample
        self._is_bplus = is_bplus
        self._hadron_id= hadron_id
        self._cfg      = cfg
        self._l_kind   = ['PassFail', 'FailPass', 'FailFail']
        self._rdf      = rdf
    # --------------------------------
    def _filter_rdf(self, rdf : RDataFrame) -> RDataFrame:
        bid = self._b_id if self._is_bplus else - self._b_id
        rdf = rdf.Filter('block > 0', 'block')
        rdf = rdf.Filter(f'B_ID=={bid}', f'B_ID=={bid}')

        return rdf
    # --------------------------------
    def _get_cuts(self, kind : str) -> tuple[str,str]:
        '''
        Parameters
        -----------------
        kind: PassFail/FailPass/FailFail

        Returns
        -----------------
        Cut for the OS or SS candidates needed to get the data in the corresponding region
        '''
        pass_cut = self._cfg['lepton_tagging']['pass']
        fail_cut = self._cfg['lepton_tagging']['fail']
        hadr_tag = self._cfg['hadron_tagging'][self._hadron_id]

        fail_cut = f'({fail_cut}) && ({hadr_tag})'

        lep_ss   = self._cfg['tracks']['ss']
        lep_os   = self._cfg['tracks']['os']

        if   kind == 'PassFail':
            cut_ss   = pass_cut.replace('LEP_', lep_ss + '_')
            cut_os   = fail_cut.replace('LEP_', lep_os + '_')
        elif kind == 'FailPass':
            cut_ss   = fail_cut.replace('LEP_', lep_ss + '_')
            cut_os   = pass_cut.replace('LEP_', lep_os + '_')
        elif kind == 'FailFail':
            cut_ss   = fail_cut.replace('LEP_', lep_ss + '_')
            cut_os   = fail_cut.replace('LEP_', lep_os + '_')
        else:
            raise ValueError(f'Invalid kind: {kind}')

        log.debug(f'Kind: {kind}')
        log.debug(f'SS cut: {cut_ss}')
        log.debug(f'OS cut: {cut_os}')

        return cut_ss, cut_os
    # --------------------------------
    def _rdf_to_df(self, rdf : RDataFrame) -> pnd.DataFrame:
        '''
        Parameters
        ---------------
        rdf: ROOT dataframe

        Returns
        ---------------
        Pandas dataframe with subset of columns
        '''
        l_branch = self._cfg['branches']
        log.debug('Storing branches')
        data     = rdf.AsNumpy(l_branch)
        df       = pnd.DataFrame(data)

        if len(df) == 0:
            rep      = rdf.Report()
            cutflow  = ut.rdf_report_to_df(rep)
            log.warning('Empty dataset:\n')
            log.info(cutflow)

        return df
    # --------------------------------
    def _hadron_from_sample(self) -> str:
        '''
        Returns name of misID hadron, given an MC sample
        Needed to pick PID maps with efficiencies
        '''
        if self._sample == 'Bu_piplpimnKpl_eq_sqDalitz_DPC':
            return 'Pi'

        if self._sample == 'Bu_KplKplKmn_eq_sqDalitz_DPC':
            return 'K'

        # TODO: Efficiency maps from electrons should be named such that
        # this switch could happen easily
        if self._sample in ['Bu_Kee_eq_btosllball05_DPC', 'Bu_JpsiK_ee_eq_DPC']:
            return 'E'

        raise ValueError(f'Unrecognized sample: {self._sample}')
    # --------------------------------
    def get_samples(self) -> pnd.DataFrame:
        '''
        For data: Returns pandas dataframe with data split by:

        PassFail: Pass (SS), Fail (OS)
        FailPass: Fail (SS), Pass (OS)
        FailFail: Both electrons fail the PID cut

        Where:
            - SS means same sign as the B and OS is opposite sign
            - These strings are stored in the column "kind"

        For MC: It will only filter by charge and return dataframe without
        PassFail, etc split
        '''
        parquet_path = f'{self._out_path}/sample.parquet'
        if self._copy_from_cache():
            log.warning('Cached object found')
            df = pnd.read_parquet(parquet_path, engine='pyarrow')

            return df

        l_df = []
        self._rdf = self._filter_rdf(rdf=self._rdf)

        if not self._sample.startswith('DATA_'):
            df = self._rdf_to_df(rdf=self._rdf)
            df['hadron'] = self._hadron_from_sample()
            df.to_parquet(parquet_path, engine='pyarrow')

            self._cache()
            return df

        for kind in self._l_kind:
            log.info(f'Calculating sample: {kind}')
            rdf            = self._rdf
            cut_os, cut_ss = self._get_cuts(kind=kind)

            rdf = rdf.Filter(cut_os, f'OS {kind}')
            rdf = rdf.Filter(cut_ss, f'SS {kind}')

            df = self._rdf_to_df(rdf=rdf)
            df['kind'] = kind
            l_df.append(df)

        df_tot           = pnd.concat(l_df)
        df_tot['hadron'] = self._hadron_id
        df_tot.to_parquet(parquet_path, engine='pyarrow')

        self._cache()

        return df_tot
# --------------------------------
