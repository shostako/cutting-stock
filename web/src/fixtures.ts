// 実ソルバ(solver.cli)の出力をそのまま埋め込んだ開発用フィクスチャ（スキーマ完全一致）。
// バックエンド未起動でもUI単体で描画・確認できる。
import type { SolveOk } from './api/types'

export const SAMPLE: SolveOk = {
  "status": "OK",
  "validation": [],
  "input_echo": {
    "length": 1200,
    "kerf": 5,
    "total_demand_length": 6960
  },
  "lower_bound_bins": 6,
  "pareto": {
    "material_optimal_idx": 0,
    "recommended_index": 0,
    "solutions": [
      {
        "bars_used": 6,
        "total_waste": 130,
        "waste_ratio": 0.018056,
        "num_pattern_types": 4,
        "optimality": {
          "status": "OPTIMAL",
          "mip_gap": 0.0,
          "lp_lower_bound": 6.0,
          "proven_optimal": true,
          "timed_out": false
        },
        "patterns": [
          {
            "cuts": [
              500,
              210,
              210,
              210
            ],
            "item_counts": {
              "210": 3,
              "500": 1
            },
            "stock_length": 1200,
            "waste": 50,
            "run_count": 2,
            "segments": [
              {
                "kind": "piece",
                "offset": 0,
                "length": 500,
                "item_length": 500,
                "label": "A"
              },
              {
                "kind": "kerf",
                "offset": 500,
                "length": 5,
                "item_length": null,
                "label": ""
              },
              {
                "kind": "piece",
                "offset": 505,
                "length": 210,
                "item_length": 210,
                "label": "D"
              },
              {
                "kind": "kerf",
                "offset": 715,
                "length": 5,
                "item_length": null,
                "label": ""
              },
              {
                "kind": "piece",
                "offset": 720,
                "length": 210,
                "item_length": 210,
                "label": "D"
              },
              {
                "kind": "kerf",
                "offset": 930,
                "length": 5,
                "item_length": null,
                "label": ""
              },
              {
                "kind": "piece",
                "offset": 935,
                "length": 210,
                "item_length": 210,
                "label": "D"
              },
              {
                "kind": "kerf",
                "offset": 1145,
                "length": 5,
                "item_length": null,
                "label": ""
              },
              {
                "kind": "waste",
                "offset": 1150,
                "length": 50,
                "item_length": null,
                "label": ""
              }
            ]
          },
          {
            "cuts": [
              500,
              340,
              340
            ],
            "item_counts": {
              "340": 2,
              "500": 1
            },
            "stock_length": 1200,
            "waste": 5,
            "run_count": 2,
            "segments": [
              {
                "kind": "piece",
                "offset": 0,
                "length": 500,
                "item_length": 500,
                "label": "A"
              },
              {
                "kind": "kerf",
                "offset": 500,
                "length": 5,
                "item_length": null,
                "label": ""
              },
              {
                "kind": "piece",
                "offset": 505,
                "length": 340,
                "item_length": 340,
                "label": "B"
              },
              {
                "kind": "kerf",
                "offset": 845,
                "length": 5,
                "item_length": null,
                "label": ""
              },
              {
                "kind": "piece",
                "offset": 850,
                "length": 340,
                "item_length": 340,
                "label": "B"
              },
              {
                "kind": "kerf",
                "offset": 1190,
                "length": 5,
                "item_length": null,
                "label": ""
              },
              {
                "kind": "waste",
                "offset": 1195,
                "length": 5,
                "item_length": null,
                "label": ""
              }
            ]
          },
          {
            "cuts": [
              340,
              340,
              290,
              210
            ],
            "item_counts": {
              "210": 1,
              "290": 1,
              "340": 2
            },
            "stock_length": 1200,
            "waste": 0,
            "run_count": 1,
            "segments": [
              {
                "kind": "piece",
                "offset": 0,
                "length": 340,
                "item_length": 340,
                "label": "B"
              },
              {
                "kind": "kerf",
                "offset": 340,
                "length": 5,
                "item_length": null,
                "label": ""
              },
              {
                "kind": "piece",
                "offset": 345,
                "length": 340,
                "item_length": 340,
                "label": "B"
              },
              {
                "kind": "kerf",
                "offset": 685,
                "length": 5,
                "item_length": null,
                "label": ""
              },
              {
                "kind": "piece",
                "offset": 690,
                "length": 290,
                "item_length": 290,
                "label": "C"
              },
              {
                "kind": "kerf",
                "offset": 980,
                "length": 5,
                "item_length": null,
                "label": ""
              },
              {
                "kind": "piece",
                "offset": 985,
                "length": 210,
                "item_length": 210,
                "label": "D"
              },
              {
                "kind": "kerf",
                "offset": 1195,
                "length": 5,
                "item_length": null,
                "label": ""
              }
            ]
          },
          {
            "cuts": [
              290,
              290,
              290,
              290
            ],
            "item_counts": {
              "290": 4
            },
            "stock_length": 1200,
            "waste": 20,
            "run_count": 1,
            "segments": [
              {
                "kind": "piece",
                "offset": 0,
                "length": 290,
                "item_length": 290,
                "label": "C"
              },
              {
                "kind": "kerf",
                "offset": 290,
                "length": 5,
                "item_length": null,
                "label": ""
              },
              {
                "kind": "piece",
                "offset": 295,
                "length": 290,
                "item_length": 290,
                "label": "C"
              },
              {
                "kind": "kerf",
                "offset": 585,
                "length": 5,
                "item_length": null,
                "label": ""
              },
              {
                "kind": "piece",
                "offset": 590,
                "length": 290,
                "item_length": 290,
                "label": "C"
              },
              {
                "kind": "kerf",
                "offset": 880,
                "length": 5,
                "item_length": null,
                "label": ""
              },
              {
                "kind": "piece",
                "offset": 885,
                "length": 290,
                "item_length": 290,
                "label": "C"
              },
              {
                "kind": "kerf",
                "offset": 1175,
                "length": 5,
                "item_length": null,
                "label": ""
              },
              {
                "kind": "waste",
                "offset": 1180,
                "length": 20,
                "item_length": null,
                "label": ""
              }
            ]
          }
        ]
      },
      {
        "bars_used": 7,
        "total_waste": 690,
        "waste_ratio": 0.082143,
        "num_pattern_types": 2,
        "optimality": {
          "status": "OPTIMAL",
          "mip_gap": 0.0,
          "lp_lower_bound": 6.0,
          "proven_optimal": false,
          "timed_out": false
        },
        "patterns": [
          {
            "cuts": [
              500,
              340,
              210
            ],
            "item_counts": {
              "210": 1,
              "340": 1,
              "500": 1
            },
            "stock_length": 1200,
            "waste": 135,
            "run_count": 4,
            "segments": [
              {
                "kind": "piece",
                "offset": 0,
                "length": 500,
                "item_length": 500,
                "label": "A"
              },
              {
                "kind": "kerf",
                "offset": 500,
                "length": 5,
                "item_length": null,
                "label": ""
              },
              {
                "kind": "piece",
                "offset": 505,
                "length": 340,
                "item_length": 340,
                "label": "B"
              },
              {
                "kind": "kerf",
                "offset": 845,
                "length": 5,
                "item_length": null,
                "label": ""
              },
              {
                "kind": "piece",
                "offset": 850,
                "length": 210,
                "item_length": 210,
                "label": "D"
              },
              {
                "kind": "kerf",
                "offset": 1060,
                "length": 5,
                "item_length": null,
                "label": ""
              },
              {
                "kind": "waste",
                "offset": 1065,
                "length": 135,
                "item_length": null,
                "label": ""
              }
            ]
          },
          {
            "cuts": [
              340,
              290,
              290,
              210
            ],
            "item_counts": {
              "210": 1,
              "290": 2,
              "340": 1
            },
            "stock_length": 1200,
            "waste": 50,
            "run_count": 3,
            "segments": [
              {
                "kind": "piece",
                "offset": 0,
                "length": 340,
                "item_length": 340,
                "label": "B"
              },
              {
                "kind": "kerf",
                "offset": 340,
                "length": 5,
                "item_length": null,
                "label": ""
              },
              {
                "kind": "piece",
                "offset": 345,
                "length": 290,
                "item_length": 290,
                "label": "C"
              },
              {
                "kind": "kerf",
                "offset": 635,
                "length": 5,
                "item_length": null,
                "label": ""
              },
              {
                "kind": "piece",
                "offset": 640,
                "length": 290,
                "item_length": 290,
                "label": "C"
              },
              {
                "kind": "kerf",
                "offset": 930,
                "length": 5,
                "item_length": null,
                "label": ""
              },
              {
                "kind": "piece",
                "offset": 935,
                "length": 210,
                "item_length": 210,
                "label": "D"
              },
              {
                "kind": "kerf",
                "offset": 1145,
                "length": 5,
                "item_length": null,
                "label": ""
              },
              {
                "kind": "waste",
                "offset": 1150,
                "length": 50,
                "item_length": null,
                "label": ""
              }
            ]
          }
        ]
      }
    ]
  },
  "meta": {
    "material_solver": "arcflow+HiGHS"
  }
} as SolveOk
