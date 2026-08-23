// GENERATED FILE — do not edit by hand.
// Produced by `python web/pitch/build_data.py`, which reads only the committed
// results/*.json files. Every `source` field below is a real path in this repo.
// If a number on a slide is questioned, open the file named in its `source`.

export const DATA = {
  "generatedFrom": "committed results files; see each block's `source`",
  "h1": {
    "adult": {
      "source": "results/h1_all_families.json",
      "dataset": "adult",
      "label": "UCI Adult",
      "nRows": 6000,
      "seeds": 5,
      "epsGrid": [
        0.5,
        1.0,
        2.0,
        4.0,
        8.0
      ],
      "mechanisms": [
        "independent",
        "pairwise",
        "aim"
      ],
      "corrCols": [
        "age",
        "hours_per_week"
      ],
      "trueCorrelation": 0.10343557488146334,
      "trtrF1": 0.6603832306954429,
      "cells": [
        {
          "mechanism": "independent",
          "eps": 0.5,
          "proved": 0.45588471463440106,
          "audited": 0.0,
          "corrErr": {
            "mean": 0.09342531461934683,
            "lo": 0.08016769675518126,
            "hi": 0.10632018530486312,
            "n": 5
          },
          "tstrF1": {
            "mean": 0.4718523426939205,
            "lo": 0.41733815838685107,
            "hi": 0.5246766549401847,
            "n": 5
          },
          "miaAuc": 0.495875
        },
        {
          "mechanism": "independent",
          "eps": 1.0,
          "proved": 0.9122542470732562,
          "audited": 0.0,
          "corrErr": {
            "mean": 0.09302495852791279,
            "lo": 0.08165434615020455,
            "hi": 0.10439557090562104,
            "n": 5
          },
          "tstrF1": {
            "mean": 0.46996225859395535,
            "lo": 0.43180437645432884,
            "hi": 0.5081201407335818,
            "n": 5
          },
          "miaAuc": 0.5039975
        },
        {
          "mechanism": "independent",
          "eps": 2.0,
          "proved": 1.827533823411445,
          "audited": 0.0,
          "corrErr": {
            "mean": 0.09391365038898027,
            "lo": 0.08178481951437336,
            "hi": 0.10567919694973191,
            "n": 5
          },
          "tstrF1": {
            "mean": 0.4263869216450898,
            "lo": 0.33954403100760944,
            "hi": 0.5037018551978776,
            "n": 5
          },
          "miaAuc": 0.5022212500000001
        },
        {
          "mechanism": "independent",
          "eps": 4.0,
          "proved": 3.663710008556676,
          "audited": 0.0,
          "corrErr": {
            "mean": 0.09353695922068604,
            "lo": 0.08076812793633603,
            "hi": 0.10568732834842665,
            "n": 5
          },
          "tstrF1": {
            "mean": 0.4670008584027684,
            "lo": 0.35177902577008513,
            "hi": 0.5751517383459641,
            "n": 5
          },
          "miaAuc": 0.5003425
        },
        {
          "mechanism": "independent",
          "eps": 8.0,
          "proved": 7.3559535878149775,
          "audited": 0.0,
          "corrErr": {
            "mean": 0.0946568035017353,
            "lo": 0.08170413308173363,
            "hi": 0.1070805028317197,
            "n": 5
          },
          "tstrF1": {
            "mean": 0.4064649619231472,
            "lo": 0.2967101464564686,
            "hi": 0.5151546887447854,
            "n": 5
          },
          "miaAuc": 0.500105
        },
        {
          "mechanism": "pairwise",
          "eps": 0.5,
          "proved": 0.45588471463440106,
          "audited": 0.0,
          "corrErr": {
            "mean": 0.061054194544435725,
            "lo": 0.02185342221653119,
            "hi": 0.11433553424308271,
            "n": 5
          },
          "tstrF1": {
            "mean": 0.4829747572570473,
            "lo": 0.3800231936085595,
            "hi": 0.5679552194035205,
            "n": 5
          },
          "miaAuc": 0.4936475000000001
        },
        {
          "mechanism": "pairwise",
          "eps": 1.0,
          "proved": 0.9122542470732562,
          "audited": 0.015177059535813548,
          "corrErr": {
            "mean": 0.06940762509739339,
            "lo": 0.037995371610691483,
            "hi": 0.12125811075260132,
            "n": 5
          },
          "tstrF1": {
            "mean": 0.42766173181201805,
            "lo": 0.3511614109592472,
            "hi": 0.49860631195020766,
            "n": 5
          },
          "miaAuc": 0.4911575
        },
        {
          "mechanism": "pairwise",
          "eps": 2.0,
          "proved": 1.827533823411445,
          "audited": 0.0,
          "corrErr": {
            "mean": 0.04932657666372492,
            "lo": 0.017035031923635185,
            "hi": 0.09501212190191537,
            "n": 5
          },
          "tstrF1": {
            "mean": 0.41813196034885536,
            "lo": 0.33504789407783797,
            "hi": 0.4679850143416749,
            "n": 5
          },
          "miaAuc": 0.4915425
        },
        {
          "mechanism": "pairwise",
          "eps": 4.0,
          "proved": 3.663710008556676,
          "audited": 0.0,
          "corrErr": {
            "mean": 0.0197224762222984,
            "lo": 0.004769715900145704,
            "hi": 0.04636314366378056,
            "n": 5
          },
          "tstrF1": {
            "mean": 0.42675565167118235,
            "lo": 0.36201468787863356,
            "hi": 0.47734180652708635,
            "n": 5
          },
          "miaAuc": 0.48865625
        },
        {
          "mechanism": "pairwise",
          "eps": 8.0,
          "proved": 7.3559535878149775,
          "audited": 0.0,
          "corrErr": {
            "mean": 0.028267420023339717,
            "lo": 0.013189929029986391,
            "hi": 0.05172697322436602,
            "n": 5
          },
          "tstrF1": {
            "mean": 0.4321468927240977,
            "lo": 0.36831013013060454,
            "hi": 0.4781040454233845,
            "n": 5
          },
          "miaAuc": 0.49248875000000003
        },
        {
          "mechanism": "aim",
          "eps": 0.5,
          "proved": 0.38534588280692106,
          "audited": 0.0,
          "corrErr": {
            "mean": 0.08267253963411507,
            "lo": 0.02580866139821541,
            "hi": 0.13953641787001475,
            "n": 5
          },
          "tstrF1": {
            "mean": 0.4976755508095618,
            "lo": 0.47793372126928346,
            "hi": 0.5174173803498401,
            "n": 5
          },
          "miaAuc": 0.4877762499999999
        },
        {
          "mechanism": "aim",
          "eps": 1.0,
          "proved": 0.7781757068329299,
          "audited": 0.0,
          "corrErr": {
            "mean": 0.04244948831194656,
            "lo": 0.014186566303072398,
            "hi": 0.07081931097823266,
            "n": 5
          },
          "tstrF1": {
            "mean": 0.5403160553053341,
            "lo": 0.5145578580021576,
            "hi": 0.5651389298883261,
            "n": 5
          },
          "miaAuc": 0.494155
        },
        {
          "mechanism": "aim",
          "eps": 2.0,
          "proved": 1.5761918554915184,
          "audited": 0.0,
          "corrErr": {
            "mean": 0.05642020128486837,
            "lo": 0.013858994385180326,
            "hi": 0.10067417213062049,
            "n": 5
          },
          "tstrF1": {
            "mean": 0.46995845884659426,
            "lo": 0.4448787766468742,
            "hi": 0.4962307123290056,
            "n": 5
          },
          "miaAuc": 0.4907125
        },
        {
          "mechanism": "aim",
          "eps": 4.0,
          "proved": 3.201144720066901,
          "audited": 0.0,
          "corrErr": {
            "mean": 0.025955155328871504,
            "lo": 0.0015101518778062456,
            "hi": 0.06810645172749857,
            "n": 5
          },
          "tstrF1": {
            "mean": 0.4598668332134809,
            "lo": 0.44048883268416156,
            "hi": 0.4816034507866007,
            "n": 5
          },
          "miaAuc": 0.49322625000000003
        },
        {
          "mechanism": "aim",
          "eps": 8.0,
          "proved": 6.5426925748221745,
          "audited": 0.0,
          "corrErr": {
            "mean": 0.00781899168595442,
            "lo": 0.0031011754138930677,
            "hi": 0.012536807958015775,
            "n": 5
          },
          "tstrF1": {
            "mean": 0.5048724230010384,
            "lo": 0.46827928668173274,
            "hi": 0.5438516995225722,
            "n": 5
          },
          "miaAuc": 0.50040625
        }
      ]
    },
    "acs": {
      "source": "results/acs/h1_all_families.json",
      "dataset": "acs",
      "label": "ACSIncome (CA 2018)",
      "nRows": 6000,
      "seeds": 5,
      "epsGrid": [
        0.5,
        1.0,
        2.0,
        4.0,
        8.0
      ],
      "mechanisms": [
        "independent",
        "pairwise",
        "aim"
      ],
      "corrCols": [
        "AGEP",
        "WKHP"
      ],
      "trueCorrelation": 0.07207986920920266,
      "trtrF1": 0.7246400901050978,
      "cells": [
        {
          "mechanism": "independent",
          "eps": 0.5,
          "proved": 0.4558899343630535,
          "audited": 0.0,
          "corrErr": {
            "mean": 0.052069997091320167,
            "lo": 0.04548731914342528,
            "hi": 0.05819248576794924,
            "n": 5
          },
          "tstrF1": {
            "mean": 0.43970555056730704,
            "lo": 0.4216835666610191,
            "hi": 0.4598669262110695,
            "n": 5
          },
          "miaAuc": 0.498715625
        },
        {
          "mechanism": "independent",
          "eps": 1.0,
          "proved": 0.9122464987698526,
          "audited": 0.0,
          "corrErr": {
            "mean": 0.053072729150054364,
            "lo": 0.04604617298128659,
            "hi": 0.06059511082384141,
            "n": 5
          },
          "tstrF1": {
            "mean": 0.4411101662261231,
            "lo": 0.4170669100378322,
            "hi": 0.4651534224144142,
            "n": 5
          },
          "miaAuc": 0.500013125
        },
        {
          "mechanism": "independent",
          "eps": 2.0,
          "proved": 1.8275208694902147,
          "audited": 0.0,
          "corrErr": {
            "mean": 0.053029642480925496,
            "lo": 0.04646531041185692,
            "hi": 0.06011344330276176,
            "n": 5
          },
          "tstrF1": {
            "mean": 0.43048004607986484,
            "lo": 0.41226006859209613,
            "hi": 0.4511528752607508,
            "n": 5
          },
          "miaAuc": 0.5027693750000001
        },
        {
          "mechanism": "independent",
          "eps": 4.0,
          "proved": 3.663921397536015,
          "audited": 0.0,
          "corrErr": {
            "mean": 0.053637054581392465,
            "lo": 0.047323004136064085,
            "hi": 0.060509271177032996,
            "n": 5
          },
          "tstrF1": {
            "mean": 0.44161847569451557,
            "lo": 0.42298490560493135,
            "hi": 0.4629020360930191,
            "n": 5
          },
          "miaAuc": 0.501850625
        },
        {
          "mechanism": "independent",
          "eps": 8.0,
          "proved": 7.356396403533938,
          "audited": 0.0,
          "corrErr": {
            "mean": 0.05349790296769017,
            "lo": 0.04708463860620041,
            "hi": 0.06043791430914271,
            "n": 5
          },
          "tstrF1": {
            "mean": 0.46159013353988065,
            "lo": 0.44893841400211454,
            "hi": 0.4744037811819967,
            "n": 5
          },
          "miaAuc": 0.503158125
        },
        {
          "mechanism": "pairwise",
          "eps": 0.5,
          "proved": 0.4558899343630535,
          "audited": 0.0,
          "corrErr": {
            "mean": 0.05428173700215973,
            "lo": 0.018648490652164774,
            "hi": 0.10876681751045925,
            "n": 5
          },
          "tstrF1": {
            "mean": 0.4663568823069495,
            "lo": 0.4454593687951623,
            "hi": 0.49671395967426835,
            "n": 5
          },
          "miaAuc": 0.49409562500000004
        },
        {
          "mechanism": "pairwise",
          "eps": 1.0,
          "proved": 0.9122464987698526,
          "audited": 0.0,
          "corrErr": {
            "mean": 0.07270844283236341,
            "lo": 0.04229502345280999,
            "hi": 0.11329931270127735,
            "n": 5
          },
          "tstrF1": {
            "mean": 0.46750835165881144,
            "lo": 0.44450598734119984,
            "hi": 0.4943872528319916,
            "n": 5
          },
          "miaAuc": 0.498014375
        },
        {
          "mechanism": "pairwise",
          "eps": 2.0,
          "proved": 1.8275208694902147,
          "audited": 0.0,
          "corrErr": {
            "mean": 0.04684727510395596,
            "lo": 0.017873412287135133,
            "hi": 0.08295440686977461,
            "n": 5
          },
          "tstrF1": {
            "mean": 0.4894401972582272,
            "lo": 0.4698851063794939,
            "hi": 0.5092642287999241,
            "n": 5
          },
          "miaAuc": 0.48960687500000005
        },
        {
          "mechanism": "pairwise",
          "eps": 4.0,
          "proved": 3.663921397536015,
          "audited": 0.042686461107149035,
          "corrErr": {
            "mean": 0.03154264949857775,
            "lo": 0.009770035103105002,
            "hi": 0.06184872999938995,
            "n": 5
          },
          "tstrF1": {
            "mean": 0.48119636098940416,
            "lo": 0.45206650572857965,
            "hi": 0.5044859965958081,
            "n": 5
          },
          "miaAuc": 0.496864375
        },
        {
          "mechanism": "pairwise",
          "eps": 8.0,
          "proved": 7.356396403533938,
          "audited": 0.0,
          "corrErr": {
            "mean": 0.020210958801563664,
            "lo": 0.00755564142752109,
            "hi": 0.03834398871462135,
            "n": 5
          },
          "tstrF1": {
            "mean": 0.5219292181889292,
            "lo": 0.497523505810607,
            "hi": 0.5466327890684914,
            "n": 5
          },
          "miaAuc": 0.497124375
        },
        {
          "mechanism": "aim",
          "eps": 0.5,
          "proved": 0.3853466544994819,
          "audited": 0.0,
          "corrErr": {
            "mean": 0.09767981039831207,
            "lo": 0.04205855322232303,
            "hi": 0.15906340322937113,
            "n": 5
          },
          "tstrF1": {
            "mean": 0.7038949027908518,
            "lo": 0.6945518690642001,
            "hi": 0.7125636108358265,
            "n": 5
          },
          "miaAuc": 0.484150625
        },
        {
          "mechanism": "aim",
          "eps": 1.0,
          "proved": 0.7781704325167329,
          "audited": 0.0,
          "corrErr": {
            "mean": 0.039494466496544346,
            "lo": 0.020429356309965663,
            "hi": 0.06945611143996806,
            "n": 5
          },
          "tstrF1": {
            "mean": 0.69179003498293,
            "lo": 0.6831397862534659,
            "hi": 0.70164966272443,
            "n": 5
          },
          "miaAuc": 0.4975706250000001
        },
        {
          "mechanism": "aim",
          "eps": 2.0,
          "proved": 1.5762727717225564,
          "audited": 0.0,
          "corrErr": {
            "mean": 0.052096976804806315,
            "lo": 0.02861622482811511,
            "hi": 0.07779956313192712,
            "n": 5
          },
          "tstrF1": {
            "mean": 0.6498387453659829,
            "lo": 0.6211767062971394,
            "hi": 0.6750396580292397,
            "n": 5
          },
          "miaAuc": 0.486081875
        },
        {
          "mechanism": "aim",
          "eps": 4.0,
          "proved": 3.201143027606534,
          "audited": 0.0,
          "corrErr": {
            "mean": 0.07324260975027318,
            "lo": 0.06302194896503219,
            "hi": 0.08752231369100202,
            "n": 5
          },
          "tstrF1": {
            "mean": 0.6510441615236237,
            "lo": 0.6333133695461973,
            "hi": 0.6695960683795269,
            "n": 5
          },
          "miaAuc": 0.49160562500000005
        },
        {
          "mechanism": "aim",
          "eps": 8.0,
          "proved": 6.542736383600297,
          "audited": 0.0,
          "corrErr": {
            "mean": 0.06258672620935572,
            "lo": 0.04318816149146203,
            "hi": 0.07533630534781102,
            "n": 5
          },
          "tstrF1": {
            "mean": 0.5811672873009257,
            "lo": 0.5385551513932021,
            "hi": 0.628943769475779,
            "n": 5
          },
          "miaAuc": 0.49491187499999995
        }
      ]
    }
  },
  "h2": {
    "adult": {
      "source": "results/h2_analysis.json",
      "nTests": 14,
      "survivingBh": 0,
      "survivingBonferroni": 0,
      "minRawP": 0.22438381913715424,
      "numCanaries": 80,
      "alpha": 0.05,
      "ceiling": 3.2660561811214377,
      "mdeEpsilon": 0.007910226256157109,
      "mdeAccuracy": 0.6,
      "observedMaxEpsilon": 0.03643034289968919,
      "observedMaxAccuracy": 0.5625,
      "fractionOfRange": 0.011154230325327844,
      "seeds": [
        0,
        1,
        2
      ],
      "nRows": 6000
    },
    "acs": {
      "source": "results/acs/h2_analysis.json",
      "nTests": 22,
      "survivingBh": 0,
      "survivingBonferroni": 0,
      "minRawP": 0.1527945360354579,
      "numCanaries": 44,
      "alpha": 0.05,
      "ceiling": 2.6527653811764287,
      "mdeEpsilon": 0.005726411675859577,
      "mdeAccuracy": 0.6363636363636364,
      "observedMaxEpsilon": 0.09644003601626433,
      "observedMaxAccuracy": 0.5909090909090909,
      "fractionOfRange": 0.03635452901360459,
      "seeds": [
        0,
        1,
        2
      ],
      "nRows": 6000
    }
  },
  "h3": {
    "adult": {
      "source": "results/h3_allocation.json",
      "label": "UCI Adult",
      "priorityWeight": 4.0,
      "weightsSource": "declared-public",
      "verdict": "H3 is NOT SUPPORTED. At none of the 5 epsilon values does the paired weighted-minus-uniform gap have a bootstrap CI excluding zero. Declaring which columns matter and spending more of a fixed budget on them did not measurably improve downstream macro F1 for this mechanism.",
      "nCells": 5
    },
    "acs": {
      "source": "results/acs/h3_allocation.json",
      "label": "ACSIncome (CA 2018)",
      "priorityWeight": 4.0,
      "weightsSource": "declared-public",
      "verdict": "H3 is NOT SUPPORTED. At none of the 5 epsilon values does the paired weighted-minus-uniform gap have a bootstrap CI excluding zero. Declaring which columns matter and spending more of a fixed budget on them did not measurably improve downstream macro F1 for this mechanism.",
      "nCells": 5
    }
  },
  "confound": {
    "adult": {
      "source": "results/clique_confound.json",
      "label": "UCI Adult",
      "confirmed": true,
      "verdict": "CONFOUND CONFIRMED. AIM beats the independent-marginal baseline on the pairs it selects as cliques, and does NOT beat it on the pairs it does not select \u2014 on those it is statistically indistinguishable from a mechanism that models no cross-column dependence at all. AIM's structure advantage therefore exists exactly where it spent a clique, and the H1 headline measured precisely such a pair. The H1 structure result must be read as a statement about clique selection.",
      "selectedPairs": [
        "age|hours_per_week"
      ],
      "unselectedPairs": [
        "age|capital_gain",
        "age|capital_loss",
        "capital_gain|capital_loss",
        "hours_per_week|capital_gain",
        "hours_per_week|capital_loss"
      ],
      "aimOnSelected": {
        "mean": 0.026307143448138785,
        "lo": 0.01607923071468931,
        "hi": 0.03817338018402021,
        "n": 25
      },
      "indepOnSelected": {
        "mean": 0.1115224371858704,
        "lo": 0.10857726713636569,
        "hi": 0.11417571651062601,
        "n": 25
      },
      "aimOnUnselected": {
        "mean": 0.05920019255008372,
        "lo": 0.05522623933158736,
        "hi": 0.0631433951012944,
        "n": 125
      },
      "indepOnUnselected": {
        "mean": 0.06086156671069653,
        "lo": 0.057006760065211,
        "hi": 0.06452716822645668,
        "n": 125
      }
    },
    "acs": {
      "source": "results/acs/clique_confound.json",
      "label": "ACSIncome (CA 2018)",
      "confirmed": false,
      "verdict": "INCONCLUSIVE: AIM does not separate from the baseline even on the pairs it selects, so this design cannot speak to the confound either way.",
      "selectedPairs": [],
      "unselectedPairs": [
        "AGEP|SCHL",
        "AGEP|WKHP",
        "WKHP|SCHL"
      ],
      "aimOnSelected": null,
      "indepOnSelected": null,
      "aimOnUnselected": {
        "mean": 0.03895448269869883,
        "lo": 0.03262769190632882,
        "hi": 0.04591378691547356,
        "n": 75
      },
      "indepOnUnselected": {
        "mean": 0.05188554384060365,
        "lo": 0.04546373884911638,
        "hi": 0.058167430931759266,
        "n": 75
      }
    }
  },
  "floor": {
    "source": "results/detection_floor.json",
    "alpha": 0.05,
    "nRows": 3000,
    "floors": {
      "0.0": null,
      "0.01": null,
      "0.05": null,
      "0.25": 400,
      "1.0": 10
    },
    "cells": [
      {
        "leak": 0.0,
        "r": 10,
        "detectionRate": 0.0,
        "meanEps": 0.0,
        "tpr": 0.54,
        "fpr": 0.45999999999999996
      },
      {
        "leak": 0.0,
        "r": 25,
        "detectionRate": 0.0,
        "meanEps": 0.0,
        "tpr": 0.52,
        "fpr": 0.48
      },
      {
        "leak": 0.0,
        "r": 50,
        "detectionRate": 0.0,
        "meanEps": 0.0,
        "tpr": 0.476,
        "fpr": 0.524
      },
      {
        "leak": 0.0,
        "r": 100,
        "detectionRate": 0.2,
        "meanEps": 0.013974237791235128,
        "tpr": 0.5279999999999999,
        "fpr": 0.4720000000000001
      },
      {
        "leak": 0.0,
        "r": 200,
        "detectionRate": 0.0,
        "meanEps": 0.0,
        "tpr": 0.51,
        "fpr": 0.48999999999999994
      },
      {
        "leak": 0.0,
        "r": 400,
        "detectionRate": 0.0,
        "meanEps": 0.0,
        "tpr": 0.499,
        "fpr": 0.501
      },
      {
        "leak": 0.0,
        "r": 800,
        "detectionRate": 0.0,
        "meanEps": 0.0,
        "tpr": 0.48674999999999996,
        "fpr": 0.51325
      },
      {
        "leak": 0.01,
        "r": 10,
        "detectionRate": 0.0,
        "meanEps": 0.0,
        "tpr": 0.5,
        "fpr": 0.5
      },
      {
        "leak": 0.01,
        "r": 25,
        "detectionRate": 0.0,
        "meanEps": 0.0,
        "tpr": 0.52,
        "fpr": 0.48
      },
      {
        "leak": 0.01,
        "r": 50,
        "detectionRate": 0.0,
        "meanEps": 0.0,
        "tpr": 0.492,
        "fpr": 0.508
      },
      {
        "leak": 0.01,
        "r": 100,
        "detectionRate": 0.2,
        "meanEps": 0.005852001185048372,
        "tpr": 0.52,
        "fpr": 0.48
      },
      {
        "leak": 0.01,
        "r": 200,
        "detectionRate": 0.0,
        "meanEps": 0.0,
        "tpr": 0.5039999999999999,
        "fpr": 0.496
      },
      {
        "leak": 0.01,
        "r": 400,
        "detectionRate": 0.0,
        "meanEps": 0.0,
        "tpr": 0.49399999999999994,
        "fpr": 0.506
      },
      {
        "leak": 0.01,
        "r": 800,
        "detectionRate": 0.0,
        "meanEps": 0.0,
        "tpr": 0.49949999999999994,
        "fpr": 0.5005
      },
      {
        "leak": 0.05,
        "r": 10,
        "detectionRate": 0.0,
        "meanEps": 0.0,
        "tpr": 0.56,
        "fpr": 0.43999999999999995
      },
      {
        "leak": 0.05,
        "r": 25,
        "detectionRate": 0.0,
        "meanEps": 0.0,
        "tpr": 0.512,
        "fpr": 0.488
      },
      {
        "leak": 0.05,
        "r": 50,
        "detectionRate": 0.0,
        "meanEps": 0.0,
        "tpr": 0.528,
        "fpr": 0.4720000000000001
      },
      {
        "leak": 0.05,
        "r": 100,
        "detectionRate": 0.2,
        "meanEps": 0.005852001185048372,
        "tpr": 0.5299999999999999,
        "fpr": 0.47000000000000003
      },
      {
        "leak": 0.05,
        "r": 200,
        "detectionRate": 0.0,
        "meanEps": 0.0,
        "tpr": 0.48999999999999994,
        "fpr": 0.51
      },
      {
        "leak": 0.05,
        "r": 400,
        "detectionRate": 0.0,
        "meanEps": 0.0,
        "tpr": 0.51,
        "fpr": 0.49000000000000005
      },
      {
        "leak": 0.05,
        "r": 800,
        "detectionRate": 0.0,
        "meanEps": 0.0,
        "tpr": 0.5095000000000001,
        "fpr": 0.49050000000000005
      },
      {
        "leak": 0.25,
        "r": 10,
        "detectionRate": 0.0,
        "meanEps": 0.0,
        "tpr": 0.62,
        "fpr": 0.38
      },
      {
        "leak": 0.25,
        "r": 25,
        "detectionRate": 0.0,
        "meanEps": 0.0,
        "tpr": 0.5680000000000001,
        "fpr": 0.43200000000000005
      },
      {
        "leak": 0.25,
        "r": 50,
        "detectionRate": 0.0,
        "meanEps": 0.0,
        "tpr": 0.5800000000000001,
        "fpr": 0.42000000000000004
      },
      {
        "leak": 0.25,
        "r": 100,
        "detectionRate": 0.2,
        "meanEps": 0.030360654462966218,
        "tpr": 0.576,
        "fpr": 0.42400000000000004
      },
      {
        "leak": 0.25,
        "r": 200,
        "detectionRate": 0.4,
        "meanEps": 0.029496641985590166,
        "tpr": 0.57,
        "fpr": 0.43000000000000005
      },
      {
        "leak": 0.25,
        "r": 400,
        "detectionRate": 0.8,
        "meanEps": 0.07177164344905886,
        "tpr": 0.5655,
        "fpr": 0.4345
      },
      {
        "leak": 0.25,
        "r": 800,
        "detectionRate": 1.0,
        "meanEps": 0.1367606068292907,
        "tpr": 0.56925,
        "fpr": 0.43075
      },
      {
        "leak": 1.0,
        "r": 10,
        "detectionRate": 1.0,
        "meanEps": 0.807154865248952,
        "tpr": 1.0,
        "fpr": 0.0
      },
      {
        "leak": 1.0,
        "r": 25,
        "detectionRate": 1.0,
        "meanEps": 1.8388684705889868,
        "tpr": 1.0,
        "fpr": 0.0
      },
      {
        "leak": 1.0,
        "r": 50,
        "detectionRate": 1.0,
        "meanEps": 2.5695846830164917,
        "tpr": 1.0,
        "fpr": 0.0
      },
      {
        "leak": 1.0,
        "r": 100,
        "detectionRate": 1.0,
        "meanEps": 3.2813463490987878,
        "tpr": 1.0,
        "fpr": 0.0
      },
      {
        "leak": 1.0,
        "r": 200,
        "detectionRate": 1.0,
        "meanEps": 3.9837582521650896,
        "tpr": 1.0,
        "fpr": 0.0
      },
      {
        "leak": 1.0,
        "r": 400,
        "detectionRate": 1.0,
        "meanEps": 4.681527163123462,
        "tpr": 1.0,
        "fpr": 0.0
      },
      {
        "leak": 1.0,
        "r": 800,
        "detectionRate": 1.0,
        "meanEps": 5.376982551119489,
        "tpr": 1.0,
        "fpr": 0.0
      }
    ]
  },
  "mutation": {
    "kind": "targeted mutation probe (curated list, not a general sweep)",
    "score": 1.0,
    "caught": 10,
    "survived": 0,
    "equivalent_excluded": 3,
    "denominator": 10,
    "elapsed_seconds": 76.7,
    "results": [
      {
        "id": "budget-off-by-one",
        "status": "caught",
        "path": "synthproof/accounting/accountant.py",
        "danger": "A release could exceed its declared budget by 5% and still be accepted.",
        "tests": [
          "tests/test_accounting.py",
          "tests/test_accounting_properties.py",
          "tests/test_weighted_allocation.py"
        ],
        "equivalent": ""
      },
      {
        "id": "zero-noise-is-finite",
        "status": "equivalent",
        "path": "synthproof/accounting/accountant.py",
        "danger": "Zero noise would compose to a FINITE epsilon instead of infinity \u2014 a release with no protection carrying a real-looking bound. This is defect #2 from the audit history.",
        "tests": [
          "tests/test_accounting.py",
          "tests/test_accounting_properties.py",
          "tests/test_weighted_allocation.py"
        ],
        "equivalent": "Verified: dp_accounting returns inf for GaussianDpEvent(0.0) regardless, so the explicit NonPrivateDpEvent branch is defence-in-depth rather than the only protection. Removing it cannot produce a finite epsilon."
      },
      {
        "id": "unknown-mechanism-silently-gaussian",
        "status": "caught",
        "path": "synthproof/accounting/accountant.py",
        "danger": "An unrecognised mechanism would be accounted as Gaussian. Defect #3 from the audit history.",
        "tests": [
          "tests/test_accounting.py",
          "tests/test_accounting_properties.py",
          "tests/test_weighted_allocation.py"
        ],
        "equivalent": ""
      },
      {
        "id": "calibration-returns-optimistic-bracket",
        "status": "caught",
        "path": "synthproof/accounting/calibration.py",
        "danger": "Calibration would return the end of the bracket that OVERSPENDS, so every release would deliver a larger epsilon than it claims.",
        "tests": [
          "tests/test_accounting.py",
          "tests/test_accounting_properties.py",
          "tests/test_weighted_allocation.py"
        ],
        "equivalent": ""
      },
      {
        "id": "weighted-shape-exponent",
        "status": "equivalent",
        "path": "synthproof/accounting/calibration.py",
        "danger": "The weighted allocation would misprice the split, so the H3 weighted arm would not spend the same total as the uniform arm.",
        "tests": [
          "tests/test_accounting.py",
          "tests/test_accounting_properties.py",
          "tests/test_weighted_allocation.py"
        ],
        "equivalent": "Verified: the exponent sets only the SHAPE of the split. The bisection still solves for the total against the accountant, so the never-overspend property holds and both H3 arms still cost the same. The mutant changes which columns get how much noise, not how much is spent."
      },
      {
        "id": "sigma-zero-allowed",
        "status": "equivalent",
        "path": "synthproof/accounting/noise.py",
        "danger": "A sigma of exactly zero would be accepted, producing an unnoised release while the accountant charges a finite epsilon.",
        "tests": [
          "tests/test_accounting.py",
          "tests/test_accounting_properties.py",
          "tests/test_weighted_allocation.py"
        ],
        "equivalent": "Verified: with sigma=0 the sampler reaches -(|y| - 0/t)^2 / (2*0) and raises ZeroDivisionError. It fails loudly rather than silently emitting an unnoised release, so the guard is redundant with an arithmetic impossibility."
      },
      {
        "id": "category-threshold-weakened",
        "status": "caught",
        "path": "synthproof/data/profiler.py",
        "danger": "Rare categories would survive suppression, leaking values held by very few people. This is the family the un-noised-mode defect belonged to.",
        "tests": [
          "tests/test_profiler_soundness.py",
          "tests/test_data.py"
        ],
        "equivalent": ""
      },
      {
        "id": "public-bounds-ignored",
        "status": "caught",
        "path": "synthproof/data/profiler.py",
        "danger": "Declared PUBLIC bounds would be ignored and re-derived noisily from the data, spending budget to rediscover a published fact and widening ranges absurdly.",
        "tests": [
          "tests/test_profiler_soundness.py",
          "tests/test_data.py"
        ],
        "equivalent": ""
      },
      {
        "id": "empty-domain-guesses-again",
        "status": "NOT APPLIED",
        "danger": "The empty-domain fallback would again return a data-derived category rather than the public domain \u2014 the exact critical defect fixed earlier in this project."
      },
      {
        "id": "identifier-check-never-fires",
        "status": "caught",
        "path": "synthproof/data/preflight.py",
        "danger": "A column with one distinct value per row would be accepted, so identifier tables would reach the generator again.",
        "tests": [
          "tests/test_preflight.py"
        ],
        "equivalent": ""
      },
      {
        "id": "row-floor-removed",
        "status": "caught",
        "path": "synthproof/data/preflight.py",
        "danger": "Tiny tables would be released, where any usable epsilon destroys the data entirely.",
        "tests": [
          "tests/test_preflight.py"
        ],
        "equivalent": ""
      },
      {
        "id": "head-not-checked",
        "status": "caught",
        "path": "synthproof/ledger/ledger.py",
        "danger": "Truncation would go undetected again: an operator could delete the entries recording a budget overspend and still pass verification.",
        "tests": [
          "tests/test_ledger_adversarial.py",
          "tests/test_ledger.py"
        ],
        "equivalent": ""
      },
      {
        "id": "head-count-not-compared",
        "status": "caught",
        "path": "synthproof/ledger/ledger.py",
        "danger": "The signed head would stop pinning the chain LENGTH, which is the specific property that detects truncation.",
        "tests": [
          "tests/test_ledger_adversarial.py",
          "tests/test_ledger.py"
        ],
        "equivalent": ""
      },
      {
        "id": "ceiling-inflated",
        "status": "caught",
        "path": "synthproof/audit/steinke.py",
        "danger": "The reported audit ceiling would be far too high, so an uninformative audited epsilon of 0 would look like meaningful evidence of no leakage.",
        "tests": [
          "tests/test_steinke.py",
          "tests/test_subgroup_audit.py"
        ],
        "equivalent": ""
      }
    ],
    "source": "results/mutation_probe.json"
  },
  "ceilingCurve": [
    {
      "r": 5,
      "epsMax": 0.1977631228525874
    },
    {
      "r": 10,
      "epsMax": 1.051873233231709
    },
    {
      "r": 15,
      "epsMax": 1.509342382215744
    },
    {
      "r": 20,
      "epsMax": 1.8227156065028982
    },
    {
      "r": 25,
      "epsMax": 2.061174256483377
    },
    {
      "r": 30,
      "epsMax": 2.2536643625605906
    },
    {
      "r": 40,
      "epsMax": 2.554010402610483
    },
    {
      "r": 44,
      "epsMax": 2.6527653811764287
    },
    {
      "r": 50,
      "epsMax": 2.784727413270937
    },
    {
      "r": 60,
      "epsMax": 2.9720875578943553
    },
    {
      "r": 80,
      "epsMax": 3.2660561811214377
    },
    {
      "r": 100,
      "epsMax": 3.4929654311522933
    },
    {
      "r": 120,
      "epsMax": 3.677794857118592
    },
    {
      "r": 160,
      "epsMax": 3.968608844766563
    },
    {
      "r": 200,
      "epsMax": 4.193629987170997
    },
    {
      "r": 300,
      "epsMax": 4.601596732351811
    },
    {
      "r": 400,
      "epsMax": 4.890528844315768
    },
    {
      "r": 600,
      "epsMax": 5.297243472585053
    },
    {
      "r": 800,
      "epsMax": 5.585550110360456
    },
    {
      "r": 1200,
      "epsMax": 5.991639653954218
    },
    {
      "r": 2000,
      "epsMax": 6.502964732625312
    },
    {
      "r": 3000,
      "epsMax": 6.908679537024868
    },
    {
      "r": 5000,
      "epsMax": 7.419704902866642
    }
  ],
  "canariesNeeded": [
    {
      "eps": 0.5,
      "r": 7
    },
    {
      "eps": 1.0,
      "r": 10
    },
    {
      "eps": 2.0,
      "r": 24
    },
    {
      "eps": 4.0,
      "r": 166
    },
    {
      "eps": 6.543,
      "r": 2082
    },
    {
      "eps": 7.356,
      "r": 4692
    },
    {
      "eps": 8.0,
      "r": 8932
    }
  ]
} as const

export type Data = typeof DATA
