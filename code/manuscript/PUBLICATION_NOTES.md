# Manuscript and reproduction notes

**Bounding the rate loss of individual paired wireless uplink schedules** by Pooya Hejazi and Masoud Sabaei. The 19 November 2026 Article for *Communications Engineering* has six main figures. The supplement contains seven notes, sixteen numbered tables, eight supplementary figures and 51 references. Table 13a concerns paired pilots. Table 13b reports uncoded decisions on the simultaneous six-user transmission.

Figures 1–3 illustrate the receive array, the exact four-user construction and directional channel error. Figure 5 distinguishes the optimum-to-floor shortfall from the loss of the deployed decision. All figure geometry and plotted values can be regenerated from the supplied code.

The scalar reanalysis pairs the seven ceilings within the same known-channel topology. Supplementary Table 6 gives the 0.15-bit/s/Hz counts. Table 8 includes 2,176 independent fixed-filter evaluations and the correctly normalized two-user root widths. The price-mixture characterization and perturbation bound are in Supplementary Note 2. The frozen confirmatory experiment, its evaluation deadlines and original input archives retain their original definitions.

From the public GitHub checkout, use the single entry point in the `code` directory. Run `python run.py figures` for the drawings and plots, `python run.py round2-summary` for the supplementary tables, and `python run.py verify-action-rates` with the five verified inputs for the fixed-filter comparisons. Pooya Hejazi is the repository author, maintainer and contact for reproduction questions. Masoud Sabaei handles Article correspondence. The offline archival deposit is private, with DOI registration deferred until acceptance.
