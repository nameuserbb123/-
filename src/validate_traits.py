'''
Validate PROSAIL-derived and in-situ measured traits by
calculating common error metrics and plotting scatter.

@author Lukas Valentin Graf
'''

import geopandas as gpd
import matplotlib as mpl
import matplotlib.pyplot as plt
import pandas as pd

from pathlib import Path

from utils import (
    assign_macro_stages,
    bbch_confusion_matrix,
    join_with_insitu,
    plot_prediction,
    TraitLimits
)

mpl.rc('font', size=16)
plt.style.use('bmh')


def validate_data(
    _df: pd.DataFrame,
    out_dir: Path,
    trait: str,
    trait_name: str,
    trait_unit: str,
    trait_limits: TraitLimits,
) -> None:
    """
    Validate S2-based trait retrieval against in-situ reference data.

    :param _df:
        DataFrame with S2-based traits and in-situ reference
    :param out_dir:
        directory where outputs should be saved to
    :param trait:
        abbreviation of the trait to validate (DataFrame column)
    :param trait_name:
        full name of the trait for labeling axis in plot
    :param trait_unit:
        phyiscal unit of the trait
    :param trait_limits:
        limits of the trait for plotting
    """

    df = _df.copy()
    df.dropna(subset=[trait], inplace=True)

    f, ax = plt.subplots(figsize=(20, 10), ncols=2)

    df_all = df.copy()
    df_pheno = df.copy()

    _, error_stats_all = plot_prediction(
        true=df_all[trait],
        pred=df_all[f'{trait}_all'],
        trait_name=trait_name,
        trait_unit=trait_unit,
        trait_lims=trait_limits,
        ax=ax[0],
        pred_unc=None
    )
    error_stats_all['phenology_considered'] = False
    ax[0].set_title('Inversion WITHOUT phenological constraints')

    _, error_stats_pheno = plot_prediction(
        true=df_pheno[trait],
        pred=df_pheno[f'{trait} (Phenology)'],
        trait_name=trait_name,
        trait_unit=trait_unit,
        trait_lims=trait_limits,
        ax=ax[1],
        pred_unc=None
    )
    error_stats_pheno['phenology_considered'] = True
    ax[1].set_title('Inversion WITH phenological constraints')
    fname_scatter = out_dir.joinpath(
        f'{trait.replace(" ","-")}_scatterplot.png')
    f.savefig(fname_scatter)
    plt.close(f)

    error_stats = pd.DataFrame([error_stats_all, error_stats_pheno])
    error_stats.to_csv(
        out_dir.joinpath(f'{trait.replace(" ","-")}_error_stats.csv'))

    # check retrieval accuracy across phenological macro stages
    # assign macro-stages to in-situ BBCH ratings
    df['BBCH Rating (Macro-Stages)'] = df['BBCH Rating'].apply(
        lambda x, assign_macro_stages=assign_macro_stages:
            assign_macro_stages(bbch_val=x)
    )
    n_macro_stages = df['Macro-Stage'].nunique()
    df_stages = df.groupby(by='Macro-Stage')
    f, ax = plt.subplots(figsize=(10*n_macro_stages, 10), ncols=n_macro_stages)
    idx = 0
    err_stats_list = []
    for macro_stage, df_stage in df_stages:
        _, err_stats = plot_prediction(
            true=df_stage[trait],
            pred=df_stage[f'{trait} (Phenology)'],
            trait_name=trait_name,
            trait_unit=trait_unit,
            trait_lims=trait_limits,
            ax=ax[idx]
        )
        ax[idx].set_title(f'Macro-Stage: {macro_stage}')
        err_stats['phase'] = macro_stage
        err_stats_list.append(err_stats)
        idx += 1
    fname_scatter_phases = out_dir.joinpath(
        f'{trait.replace(" ","-")}_scatterplot_pheno_phases.png'
    )
    f.savefig(fname_scatter_phases)
    plt.close(f)
    err_stats_df = pd.DataFrame(err_stats_list)
    fname_error_phases = out_dir.joinpath(
        f'{trait.replace(" ","-")}_errors_pheno_phases.csv'
    )
    err_stats_df.to_csv(fname_error_phases, index=False)

    # check performance of the single parametrization across all stages
    f, ax = plt.subplots(figsize=(10*n_macro_stages, 10), ncols=n_macro_stages)
    idx = 0
    err_stats_list = []
    for macro_stage, df_stage in df_stages:
        _, err_stats = plot_prediction(
            true=df_stage[trait],
            pred=df_stage[f'{trait}_all'],
            trait_name=trait_name,
            trait_unit=trait_unit,
            trait_lims=trait_limits,
            ax=ax[idx]
        )
        ax[idx].set_title(f'Macro-Stage: {macro_stage}')
        err_stats['phase'] = macro_stage
        err_stats_list.append(err_stats)
        idx += 1
    fname_scatter_phases = out_dir.joinpath(
        f'{trait.replace(" ","-")}_scatterplot_pheno_phases_all.png'
    )
    f.savefig(fname_scatter_phases)
    plt.close(f)
    err_stats_df = pd.DataFrame(err_stats_list)
    fname_error_phases = out_dir.joinpath(
        f'{trait.replace(" ","-")}_errors_pheno_phases_all.csv'
    )
    err_stats_df.to_csv(fname_error_phases, index=False)

    # check how the retrieved phenological macro stages compare to
    # in-situ BBCH ratings
    bbch_confusion_matrix(df, out_dir)


if __name__ == '__main__':

    import os
    cwd = Path(__file__).parent.absolute()
    os.chdir(cwd)

    traits = ['cab']  # ['lai', 'ccc', 'cab']

    # paths to in-situ trait measurements from 2019 and 2022

    years = [2019, 2022]

    lai_list = []
    ccc_list = []
    for year in years:
        trait_dir = Path(f'../data/in_situ_traits_{year}')
        # in-situ trait values
        fpath_insitu_lai = trait_dir.joinpath('in-situ_glai.gpkg')
        fpath_insitu_ccc = trait_dir.joinpath('in-situ_ccc.gpkg')
        lai = gpd.read_file(fpath_insitu_lai)
        if year == 2019:
            lai['gdd_cumsum'] = 999
            lai['point_id'] = lai.Plot.apply(
                lambda x: '_'.join(str(x).split('_')[0:2]))
            lai['parcel'] = lai.field
            lai['genotype'] = 'Arnold'
            lai['location'] = 'SwissFutureFarm'
        lai_list.append(lai)

        ccc = gpd.read_file(fpath_insitu_ccc)
        if year == 2019:
            ccc['gdd_cumsum'] = 999
            ccc['point_id'] = ccc.Plot.apply(
                lambda x: '_'.join(str(x).split('_')[0:2]))
            ccc['parcel'] = ccc.field
            ccc['genotype'] = 'Arnold'
            ccc['location'] = 'SwissFutureFarm'
            ccc['ccc'] = ccc['CCC [g/m2]']
        ccc_list.append(ccc)

    # combine traits from different years
    lai_all = pd.concat(lai_list)
    ccc_all = pd.concat(ccc_list)

    fpath_insitu_bbch = Path(
        '../data/in_situ_traits_2022').joinpath('in-situ_bbch.gpkg')
    bbch_insitu = gpd.read_file(fpath_insitu_bbch)

    # traits from inversion
    inv_res_dir = Path('../results/lut_based_inversion')
    sub_dirs = ['agdds_and_s2', 'agdds_only']

    # validate traits
    for sub_dir in sub_dirs:

        fpath_inv_res = inv_res_dir.joinpath(sub_dir).joinpath(
            'inv_res_gdd_insitu_points.csv')
        inv_res_df = pd.read_csv(fpath_inv_res)

        trait_settings = {
            'lai': {
                'trait_name': 'Green Leaf Area Index',
                'trait_unit': r'$m^2$ $m^{-2}$',
                'trait_limits': TraitLimits(0, 8),
                'orig_trait_data': lai_all
            },
            'ccc': {
                'trait_name': 'Canopy Chlorophyll Content',
                'trait_unit': r'$g$ $m^{-2}$',
                'trait_limits': TraitLimits(0, 4),
                'orig_trait_data': ccc_all
            },
            'cab': {
                'trait_name': 'Leaf Chlorophyll Content',
                'trait_unit': r'$\mu$ $g$ $cm^{-2}$',
                'trait_limits': TraitLimits(0, 80),
                'orig_trait_data': [lai_all, ccc_all]}
        }

        for trait in traits:

            out_dir = fpath_inv_res.parent.joinpath(f'validation_{trait}')
            out_dir.mkdir(exist_ok=True)
            # join in-situ and inversion data
            if trait == 'cab':
                insitu_trait_df = pd.merge(
                    trait_settings[trait]['orig_trait_data'][0],
                    trait_settings[trait]['orig_trait_data'][1],
                    on=['point_id', 'gdd_cumsum', 'parcel', 'location']
                )
                # replace date_x with date and drop date_y
                insitu_trait_df['date'] = insitu_trait_df['date_x']
                insitu_trait_df.drop(
                    columns=['date_x', 'date_y'], inplace=True)
                # replace lai_x with lai and drop lai_y
                insitu_trait_df['lai'] = insitu_trait_df['lai_x']
                insitu_trait_df.drop(
                    columns=['lai_x', 'lai_y'], inplace=True)

                # calculate cab from lai and ccc
                insitu_trait_df['cab'] = insitu_trait_df['ccc'] / \
                    insitu_trait_df['lai'] * 100  # [ug/cm2]
                # get all columns starting with 'lai' in inv_res_df
                lai_cols = [
                    col for col in inv_res_df.columns
                    if col.startswith('lai')]
                ccc_cols = [x.replace('lai', 'ccc') for x in lai_cols]
                for idx, lai_col in enumerate(lai_cols):
                    cab_col = lai_col.replace('lai', 'cab')
                    inv_res_df[cab_col] = \
                        inv_res_df[ccc_cols[idx]] / \
                        inv_res_df[lai_col] * 100  # [ug/cm2]
            else:
                insitu_trait_df = trait_settings[trait]['orig_trait_data']
            del trait_settings[trait]['orig_trait_data']
            fpath_joined_res = out_dir.joinpath(
                f'inv_res_joined_with_insitu_{trait}.csv')

            # join S2 and in-situ data are read data from existing file
            joined = join_with_insitu(
                insitu_trait_df, bbch_insitu, inv_res_df, [trait])
            joined.to_csv(fpath_joined_res)

            validate_data(
                _df=joined,
                out_dir=out_dir,
                trait=trait,
                **trait_settings[trait]
            )
