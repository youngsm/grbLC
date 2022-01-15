import os
import re
import sys

import lmfit as lf
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure

from .model import chisq
from .model import Model


class Lightcurve:
    _name_placeholder = "unknown grb"

    def __init__(
        self,
        filename=None,
        xdata=None,
        ydata=None,
        xerr=None,
        yerr=None,
        name=None,
        model: Model = None,
    ):
        """__init__ [summary]

        Parameters
        ----------
        filename : [type], optional
            [description], by default None
        xdata : [type], optional
            [description], by default None
        ydata : [type], optional
            [description], by default None
        xerr : [type], optional
            [description], by default None
        yerr : [type], optional
            [description], by default None
        name : [type], optional
            [description], by default None
        model : Model, optional
            [description], by default None
        """
        assert bool(filename) ^ (
            xdata is not None and ydata is not None
        ), "Either provide a filename or xdata, ydata."

        if name:
            self.name = name
        elif model is not None:
            self.name = model.name
        else:
            self.name = self._name_placeholder
        if filename:
            self.set_data(*self._read_data(filename))
        else:
            self.set_data(xdata, ydata, xerr=xerr, yerr=yerr)

        if model is not None:
            self.set_model(model)

    def set_bounds(
        self, bounds=None, xmin=-np.inf, xmax=np.inf, ymin=-np.inf, ymax=np.inf
    ):
        """set_bounds [summary]

        Parameters
        ----------
        bounds : [type], optional
            [description], by default None
        xmin : [type], optional
            [description], by default -np.inf
        xmax : [type], optional
            [description], by default np.inf
        ymin : [type], optional
            [description], by default -np.inf
        ymax : [type], optional
            [description], by default np.inf
        """
        # assert that either bounds or any of xmin, xmax, ymin, ymax is not None,
        # but prohibiting both to be true
        assert (bounds is not None) ^ any(
            np.isfinite(x) for x in [xmin, xmax, ymin, ymax]
        ), "Must provide bounds or xmin, xmax, ymin, ymax."

        if bounds is not None:
            xmin, xmax, ymin, ymax = self.model.bounds = bounds
        else:
            for i, x in enumerate([xmin, xmax, ymin, ymax]):
                if np.isfinite(x):
                    self.model.bounds[i] = x

        xmask = (xmin <= self.xdata) & (self.xdata <= xmax)
        ymask = (ymin <= self.ydata) & (self.ydata <= ymax)
        self.mask = xmask & ymask

        self.set_data(self.xdata, self.ydata, self.xerr, self.yerr)

    def set_data(self, xdata, ydata, xerr=None, yerr=None):
        """set_data [summary]

        Parameters
        ----------
        xdata : [type]
            [description]
        ydata : [type]
            [description]
        xerr : [type], optional
            [description], by default None
        yerr : [type], optional
            [description], by default None
        """
        if not hasattr(self, "mask"):
            self.mask = np.ones(len(xdata), dtype=bool)

        self.orig_xdata = np.asarray(xdata)
        self.orig_ydata = np.asarray(ydata)
        self.xdata = np.asarray(xdata)[self.mask]
        self.ydata = np.asarray(ydata)[self.mask]
        self.orig_xerr = np.asarray(xerr) if xerr is not None else None
        self.orig_yerr = np.asarray(yerr) if yerr is not None else None
        self.xerr = np.asarray(xerr)[self.mask] if xerr is not None else None
        self.yerr = np.asarray(yerr)[self.mask] if yerr is not None else None

    def set_model(self, model: Model):
        """set_model [summary]

        Parameters
        ----------
        model : Model
            [description]
        """
        self.res = None
        self.figs = {}

        self.model = model
        if self.name == self._name_placeholder:
            self.name = model.name

        self.set_bounds(self.model.bounds)

    def _read_data(self, filename):
        """_read_data [summary]

        Parameters
        ----------
        filename : [type]
            [description]
        """

        pass

    def show_data(self, fig_kwargs={}):
        """show_data [summary]

        Parameters
        ----------
        fig_kwargs : dict, optional
            [description], by default {}
        """

        fig_dict = dict(figsize=[plt.rcParams["figure.figsize"][0]] * 2)
        if bool(fig_kwargs):
            fig_dict.update(fig_kwargs)
        plot_fig = plt.figure(**fig_kwargs)
        ax = plot_fig.add_subplot(1, 1, 1)

        xmin, xmax, ymin, ymax = self.model.bounds
        logT = self.orig_xdata
        logF = self.orig_ydata
        logTerr = self.orig_xerr
        logFerr = self.orig_yerr
        logTmin, logTmax = min(logT), max(logT)
        logFmin, logFmax = min(logF), max(logF)

        mask = (logT >= xmin) & (logT <= xmax) & (logF >= ymin) & (logF <= ymax)

        # plot all data points inside xmin and xmax in black
        ax.errorbar(
            logT[mask],
            logF[mask],
            xerr=logTerr[mask] if logTerr is not None else logTerr,
            yerr=logFerr[mask] if logFerr is not None else logFerr,
            color="k",
            fmt=".",
            ms=10,
            zorder=0,
        )

        ax_xlim = ax.get_xlim()
        ax_ylim = ax.get_ylim()

        # plot all data points outside of xmin and xmax in grey
        if sum(~mask) > 0:
            ax.errorbar(
                logT[~mask],
                logF[~mask],
                xerr=logTerr[~mask] if logTerr is not None else logTerr,
                yerr=logFerr[~mask] if logFerr is not None else logFerr,
                color="k",
                fmt=".",
                alpha=0.2,
                zorder=0,
            )

        ax.set_xlim(ax_xlim)
        ax.set_ylim(ax_ylim)
        ax.set_xlabel("log T (sec)")
        ax.set_ylabel("log F (erg cm$^{-2}$ s$^{-1}$)")
        ax.set_title(self.name)
        plt.show()

    def _res(self, params):
        p = params.valuesdict().values()

        return (self.model.func(self.xdata, *p) - self.ydata) / self.sigma

    def fit(
        self,
        p0,
        run_mcmc=True,
        show=False,
        minimize_kwargs={},
        emcee_kwargs={},
    ):
        """fit [summary]

        Parameters
        ----------
        p0 : [type]
            [description]
        run_mcmc : bool, optional
            [description], by default True
        show : bool, optional
            [description], by default False
        minimize_kwargs : dict, optional
            [description], by default {}
        emcee_kwargs : dict, optional
            [description], by default {}

        Returns
        -------
        [type]
            [description]
        """

        assert self.model is not None, "No model set."
        assert self.xdata is not None, "xdata not supplied"
        assert self.ydata is not None, "ydata not supplied"
        assert np.shape(self.xdata) == np.shape(
            self.ydata
        ), "xdata and ydata not the same shape"
        if getattr(self, "yerr", None) is not None:
            assert np.shape(self.yerr) == np.shape(
                self.ydata
            ), "yerr not the same shape as input data"
        if getattr(self, "xerr", None) is not None:
            assert np.shape(self.xerr) == np.shape(
                self.xdata
            ), "xerr not the same shape as input data"
        assert len(p0) == len(
            self.model
        ), f"Initial guess not the same length as the number of arguments to {self.model.name}"

        self.p0 = p0
        self.sigma = np.sqrt(
            np.sum(
                [err ** 2 for err in [self.xerr, self.yerr] if err is not None],
                axis=0,
            )
        )
        if isinstance(self.sigma, (int, float)):
            self.sigma = 1

        self.params = lf.Parameters()
        param_details = [
            (
                p,
                p0[i],
                self.model[p].vary,
                self.model[p].min,
                self.model[p].max,
            )
            for i, p in enumerate(self.model)
        ]
        self.params.add_many(*param_details)

        minimizer = lf.Minimizer(self._res, self.params, nan_policy="propagate")

        # solve first with robust Nelder-Mead
        self.res = mi1 = minimizer.minimize(method="Nelder", **minimize_kwargs)
        self.params = self.res.params

        if run_mcmc:
            if "burn" not in emcee_kwargs:
                emcee_kwargs["burn"] = 300
            if "steps" not in emcee_kwargs:
                emcee_kwargs["steps"] = 5000
            if "thin" not in emcee_kwargs:
                emcee_kwargs["thin"] = 20

            # use emcee to probe posterior distribution
            # and find best errors
            if "progress" in emcee_kwargs:
                print("Running MCMC...")

            self.res = minimizer.minimize(
                method="emcee",
                params=mi1.params,
                is_weighted=not isinstance(self.sigma, int),
                **emcee_kwargs,
            )

            self.params = self.res.params

            # find solution to MLE & set it in self.params
            highest_prob = np.argmax(self.res.lnprob)
            highest_prob_loc = np.unravel_index(highest_prob, self.res.lnprob.shape)
            mle_soln = self.res.chain[highest_prob_loc]
            for i, name in enumerate(self.params):
                if self.params[name].vary:
                    self.params[name].value = mle_soln[i]

                    # also, calculate standard errors from emcee
                    # & set in self.params
                    quantiles = np.percentile(
                        self.res.flatchain[name], [15.865, 50, 84.135]
                    )
                    median = quantiles[1]
                    errp = abs(median - quantiles[2])
                    errm = abs(median - quantiles[0])

                    self.params[name].stderr = np.mean([errp, errm])

        if show:
            self.show_fit()

        return self.res

    def show_fit(
        self,
        detailed=None,
        print_res=True,
        show_plot=True,
        show_corner=False,
        show_chisq=False,
        xlabel=None,
        ylabel=None,
        save_plots=None,
        show=True,
        corner_kwargs={},
        chisq_kwargs={},
        fig_kwargs={},
        residual_ax_kwargs={},
        fit_ax_kwargs={},
        data_kwargs={},
        fit_kwargs={},
    ):
        """show_fit [summary]

        Parameters
        ----------
        detailed : [type], optional
            [description], by default None
        print_res : bool, optional
            [description], by default True
        show_plot : bool, optional
            [description], by default True
        show_corner : bool, optional
            [description], by default False
        show_chisq : bool, optional
            [description], by default False
        xlabel : [type], optional
            [description], by default None
        ylabel : [type], optional
            [description], by default None
        save_plots : [type], optional
            [description], by default None
        show : bool, optional
            [description], by default True
        corner_kwargs : dict, optional
            [description], by default {}
        chisq_kwargs : dict, optional
            [description], by default {}
        fig_kwargs : dict, optional
            [description], by default {}
        residual_ax_kwargs : dict, optional
            [description], by default {}
        fit_ax_kwargs : dict, optional
            [description], by default {}
        data_kwargs : dict, optional
            [description], by default {}
        fit_kwargs : dict, optional
            [description], by default {}

        Returns
        -------
        [type]
            [description]
        """
        assert getattr(self, "res", None) is not None, "No fit results found to show."

        if show_plot or detailed:

            # create figure
            fig_dict = dict(figsize=[plt.rcParams["figure.figsize"][0]] * 2)
            if bool(fig_kwargs):
                fig_dict.update(fig_kwargs)
            plot_fig = plt.figure(**fig_kwargs)
            gridspec = plt.GridSpec(nrows=2, ncols=1, height_ratios=[3, 1])

            # create axes
            ax_residual = plot_fig.add_subplot(gridspec[1], **residual_ax_kwargs)
            ax_fit = plot_fig.add_subplot(
                gridspec[0], sharex=ax_residual, **fit_ax_kwargs
            )
            plot_fig.subplots_adjust(hspace=0)

            # plot fit (within bounds first)
            if not isinstance(self.sigma, (int, float)):
                ax_fit.errorbar(
                    self.xdata, self.ydata, self.yerr, fmt="o", color="k", **fit_kwargs
                )
            else:
                ax_fit.scatter(self.xdata, self.ydata, color="k", **fit_kwargs)

            fit_ylim = ax_fit.get_ylim()

            x_vals = np.linspace(0.8 * self.xdata.min(), 1.1 * self.xdata.max(), 100)
            y_vals = self.model(x_vals, *self.params.valuesdict().values())
            ax_fit.plot(x_vals, y_vals, ls="-", color="r", label="fit")

            # plot fit (outside bounds)
            if sum(~self.mask) > 0:
                if not isinstance(self.sigma, int):
                    ax_fit.errorbar(
                        self.orig_xdata[~self.mask],
                        self.orig_ydata[~self.mask],
                        self.orig_yerr[~self.mask],
                        fmt="o",
                        color="k",
                        alpha=0.2,
                        **data_kwargs,
                    )
                else:
                    ax_fit.scatter(
                        self.orig_xdata[~self.mask],
                        self.orig_ydata[~self.mask],
                        color="k",
                        alpha=0.2,
                        **data_kwargs,
                    )

                ax_fit.set_ylim(fit_ylim)

            if self.model.name in [
                "Willingale 2007",
                "smooth broken power law",
                "simple broken power law",
            ]:

                # plot fitted T and F
                T, F, *__ = self.params.values()
                ax_fit.scatter(
                    T,
                    F,
                    c="tab:red",
                    zorder=200,
                    s=200,
                    alpha=0.5,
                    label="fitted T, F",
                )

            ax_fit.legend(framealpha=0.0)
            ax_fit.set_title(f"{self.name} Fit")

            if ylabel is None:
                ax_fit.set_ylabel("log y")
            else:
                ax_fit.set_ylabel(ylabel)

            # plot residuals
            ax_residual.axhline(
                0, color="k", linewidth=plt.rcParams["axes.linewidth"], **fit_kwargs
            )
            residuals = self.ydata - self.model(self.xdata, *self.params.values())
            full_residuals = self.orig_ydata - self.model(
                self.orig_xdata, *self.params.values()
            )

            if not isinstance(self.sigma, int):
                ax_residual.errorbar(
                    self.xdata, residuals, self.yerr, fmt="o", color="k", **fit_kwargs
                )
            else:
                ax_residual.scatter(self.xdata, residuals, color="k", **fit_kwargs)

            residual_ylim = ax_residual.get_ylim()

            if sum(~self.mask) > 0:

                if not isinstance(self.sigma, int):
                    ax_residual.errorbar(
                        self.orig_xdata[~self.mask],
                        full_residuals[~self.mask],
                        yerr=self.orig_yerr[~self.mask],
                        fmt="o",
                        color="k",
                        alpha=0.2,
                        **data_kwargs,
                    )
                else:
                    ax_residual.scatter(
                        self.orig_xdata[~self.mask],
                        full_residuals[~self.mask],
                        color="k",
                        alpha=0.2,
                        **data_kwargs,
                    )

                ax_residual.set_xlim(0.8 * self.xdata.min(), 1.1 * self.xdata.max())
                ax_residual.set_ylim(residual_ylim)

            if xlabel is None:
                ax_residual.set_xlabel("log x")
            else:
                ax_residual.set_xlabel(xlabel)

            ax_residual.set_ylabel("residuals")
            plt.setp(ax_fit.get_xticklabels(), visible=False)
            self.figs["fit"] = plot_fig

            if show:
                plt.show()

        if (show_corner or detailed) and getattr(self.res, "flatchain") is not None:
            import corner

            corner_fig = corner.corner(
                self.res.flatchain,
                labels=[
                    self.model[p].plot_fmt for p in self.model if self.model[p].vary
                ]
                + (["__lnsigma"] if isinstance(self.sigma, (int, float)) else []),
                truths=list(
                    self.params[p].value for p in self.params if self.params[p].vary
                ),
                **corner_kwargs,
            )

            self.figs["corner"] = corner_fig

            if show:
                plt.show()

        if show_chisq or detailed:  # and getattr(self.res, "flatchain") is not None:

            num_varied = sum(self.params[p].vary for p in self.params)
            fig, ax = plt.subplots(1, num_varied, figsize=(5 * num_varied, 5))

            fineness = chisq_kwargs.pop("fineness", 0.1)
            multiplier = np.arange(-2, 2, fineness)
            p, perr = np.array(
                [[self.params[p].value, self.params[p].stderr] for p in self.params]
            ).T

            paramspace = np.array(
                [p + m * perr for m in multiplier]
            )  # shape is (len(multiplier), 4)

            best_chisq = chisq(self.xdata, self.ydata, self.sigma, self.model, p)

            idx = 0
            for ax_ in list(ax):
                if not self.params[list(self.params.keys())[idx]].vary:
                    idx += 1

                chisq_params = np.tile(p, (len(multiplier), 1))
                chisq_params[:, idx] = paramspace[:, idx]
                delta_chisq = [
                    chisq(self.xdata, self.ydata, self.sigma, self.model, chisq_param)
                    - best_chisq
                    for chisq_param in chisq_params
                ]
                curr_param_fmt = self.model[list(self.params.keys())[idx]].plot_fmt
                ax_.plot(
                    multiplier,
                    delta_chisq,
                    label=curr_param_fmt + fr"={p[idx]:.3f} $\pm$ {perr[idx]:.3f}",
                    color="k",
                )
                ax_.legend(framealpha=0.0)
                ax_.set_xlabel(r"$\sigma$ multiplier")
                ax_.set_ylabel(r"$\Delta\chi^2$")
                ax_.set_title(curr_param_fmt)
                ax_.set_ylim(0, None)
                ax_.set_xlim(-2, 2)
                ax_.axvline(
                    x=-1,
                    c="k",
                    ls=":",
                    alpha=0.2,
                    linewidth=plt.rcParams["axes.linewidth"],
                    zorder=-999999,
                )
                ax_.axvline(
                    x=1,
                    c="k",
                    ls=":",
                    alpha=0.2,
                    linewidth=plt.rcParams["axes.linewidth"],
                    zorder=-999999,
                )
                idx += 1

            if show:
                plt.show()

        if print_res or detailed:
            print(lf.fit_report(self.res, show_correl=False))

        if save_plots is True:
            for fig in self.figs:
                self._savefig(self.figs[fig], suffix=fig)
        if isinstance(save_plots, str):
            for fig in self.figs:
                self._savefig(self.figs[fig], filename=save_plots, suffix=fig)

        return self.figs

    def print_fit(self, detailed=False):
        """print_fit [summary]

        Parameters
        ----------
        detailed : bool, optional
            [description], by default False
        """

        assert getattr(self, "res", None) is not None, "No fit results found."

        if detailed:
            print(lf.fit_report(self.res, show_correl=False))
        else:
            print(
                "\n".join(
                    [
                        "\t".join(
                            map(str, [x, self.params[x].value, self.params[x].stderr])
                        )
                        for x in self.params
                    ]
                )
            )

    def _savefig(self, fig, filename=None, suffix=None, format="pdf", **kwargs):
        """_savefig Wrapper around plt.savefig

        Parameters
        ----------
        fig : list
            List of matplotlib figures to save
        filename : {str, None}, optional
            File prefix for each plot, by default None
        suffix : {str, None}, optional
            [description], by default None
        format : str, optional
            [description], by default "pdf"



        """
        assert isinstance(fig, Figure), "figs must be a matplotlib Figure."
        if filename is None:
            FILE_DIR = os.path.join(os.path.dirname(os.getcwd()), "plots")

            if not os.path.exists(FILE_DIR):
                os.mkdir(FILE_DIR)

            if suffix is None:
                suffix = ""
            else:
                suffix = "_" + suffix
            filename = os.path.join(
                FILE_DIR,
                "{}{}.{}".format(
                    self.name.replace(" ", "_").replace(".", "p"), suffix, format
                ),
            )

        savefig_kwargs = dict(
            fname=filename,
            dpi=plt.rcParams["savefig.dpi"],
            metadata={f"Creator": f"grbLC v{__version__}"},
        )
        if bool(kwargs):
            savefig_kwargs.update(kwargs)

        fig.savefig(**savefig_kwargs)

    def _check_dir(self):
        if not os.path.exists(self.dir):
            best_params = self.model.func_args
            best_err = [param + "_err" for param in best_params]
            best_guesses = [param + "_guess" for param in best_params]

            header = []
            header += ["GRB", "tt", "tf"]
            for param, err in zip(best_params, best_err):
                header += [param, err]
            header += best_guesses
            header += ["chisq"]

            with open(self.dir, "w") as f:
                f.write("\t".join(header) + "\n")

    def save_fit(self, filename=None):
        """save_fit [summary]

        Parameters
        ----------
        filename : [type], optional
            [description], by default None
        """
        assert getattr(self, "res", None) is not None, "No fit results found."

    def __repr__(self):
        return f"<grbLC> {self.__class__.__name__}({self.name})"

    def prompt(self):

        self.show_data()

        auto_guess = input("want to fit? (y/[n])").lower()
        if auto_guess in ["y"]:

            if not hasattr(self.model, "func"):
                model_name = input(
                    "model to use? (i.e., W07, SIMPLE_BPL, or SMOOTH_BPL)"
                ).lower()
                self.model = getattr(Model, model_name).__init__()

            xmin = input("xmin : [-inf]")
            xmin = float(xmin) if xmin != "" else -np.inf
            xmax = input("xmax : [inf]")
            xmax = float(xmax) if xmax != "" else np.inf
            ymin = input("ymin : [-inf]")
            ymin = float(ymin) if ymin != "" else -np.inf
            ymax = input("ymax : [inf]")
            ymax = float(ymax) if ymax != "" else np.inf

            self.set_bounds(bounds=[xmin, xmax, ymin, ymax])

            param_guesses = []
            for param in self.model:
                param_guesses.append(float(input(f"init {param} : ")))

            self.fit(p0=param_guesses, run_mcmc=True)
            self.show_fit()

            if str(input("save? ([y]/n): ")) in ["", "y"]:
                self.show_fit(show=False, save_plots=True)

        else:
            from IPython import clear_output

            clear_output()
            return


major, *__ = sys.version_info
readfile_kwargs = {"encoding": "utf-8"} if major >= 3 else {}


def readfile(filename):
    with open(filename, **readfile_kwargs) as fp:
        contents = fp.read()
    return contents


version_regex = re.compile('__version__ = "(.*?)"')
contents = readfile(
    os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "__init__.py"
    )
)
__version__ = version_regex.findall(contents)[0]