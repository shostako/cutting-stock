// 実ソルバ(solver.api)の出力をそのまま埋め込んだ開発用フィクスチャ（スキーマ完全一致）。
// バックエンド未起動でもUI単体で描画・確認できる。既定スキーム=長さラベル。
// ⚠ 手で編集するな: `uv run python web/scripts/gen_fixtures.py` で再生成すること。
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
  "solution": {
    "bars_used": 6,
    "total_waste": 240,
    "waste_ratio": 0.033333,
    "num_pattern_types": 4,
    "optimality": {
      "status": "Optimal",
      "mip_gap": 0.0,
      "lp_lower_bound": 6.0,
      "proven_optimal": true,
      "patterns_min_proven": true,
      "timed_out": false
    },
    "patterns": [
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
        "run_count": 3,
        "segments": [
          {
            "kind": "piece",
            "offset": 0,
            "length": 500,
            "item_length": 500,
            "label": "500"
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
            "label": "340"
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
            "label": "340"
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
        "run_count": 1,
        "segments": [
          {
            "kind": "piece",
            "offset": 0,
            "length": 500,
            "item_length": 500,
            "label": "500"
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
            "label": "210"
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
            "label": "210"
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
            "label": "210"
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
          290,
          210,
          210,
          210,
          210
        ],
        "item_counts": {
          "210": 4,
          "290": 1
        },
        "stock_length": 1200,
        "waste": 45,
        "run_count": 1,
        "segments": [
          {
            "kind": "piece",
            "offset": 0,
            "length": 290,
            "item_length": 290,
            "label": "290"
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
            "length": 210,
            "item_length": 210,
            "label": "210"
          },
          {
            "kind": "kerf",
            "offset": 505,
            "length": 5,
            "item_length": null,
            "label": ""
          },
          {
            "kind": "piece",
            "offset": 510,
            "length": 210,
            "item_length": 210,
            "label": "210"
          },
          {
            "kind": "kerf",
            "offset": 720,
            "length": 5,
            "item_length": null,
            "label": ""
          },
          {
            "kind": "piece",
            "offset": 725,
            "length": 210,
            "item_length": 210,
            "label": "210"
          },
          {
            "kind": "kerf",
            "offset": 935,
            "length": 5,
            "item_length": null,
            "label": ""
          },
          {
            "kind": "piece",
            "offset": 940,
            "length": 210,
            "item_length": 210,
            "label": "210"
          },
          {
            "kind": "kerf",
            "offset": 1150,
            "length": 5,
            "item_length": null,
            "label": ""
          },
          {
            "kind": "waste",
            "offset": 1155,
            "length": 45,
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
            "label": "290"
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
            "label": "290"
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
            "label": "290"
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
            "label": "290"
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
  "meta": {
    "material_solver": "arcflow+HiGHS",
    "pattern_solver": "CP-SAT(pool-MIP)"
  }
}
