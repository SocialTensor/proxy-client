VALIDATORS_FEED = [
  {
    "_id": "[validator_id]",
    "generate_endpoint": "http://[validator_addr]/validator_proxy",
    "is_active": True,
    "counter": {
      "2024-06-19": {
        "success": 0,
        "failure": 0
      }
    }
  }
]

AUTH_KEYS_FEED = [
  {
    "_id": "[auth_key]",
    "request_count": 0,
    "credit": 10,
    "email": '',
    "password": ''
  }
]

MODEL_CONFIG_FEED = [
  {
    "_id": "664187aacc48740007156636",
    "name": "model_list",
    "data": {
      "JuggernautXL": {
        "supporting_pipelines": [
          "txt2img"
        ],
        "default_params": {
          "num_inference_steps": 30,
          "clip_skip": 2,
          "guidance_scale": 7
        },
        "credit_cost": 0.001
      },
      "AnimeV3": {
        "supporting_pipelines": [
          "txt2img"
        ],
        "default_params": {
          "num_inference_steps": 25,
          "clip_skip": 2,
          "guidance_scale": 7
        },
        "credit_cost": 0.001
      },
      "RealitiesEdgeXL": {
        "supporting_pipelines": [
          "txt2img"
        ],
        "default_params": {
          "num_inference_steps": 8,
          "clip_skip": 2,
          "guidance_scale": 2
        },
        "credit_cost": 0.001
      },
      "DreamShaperXL": {
        "supporting_pipelines": [
          "txt2img",
          "instantid",
          "img2img"
        ],
        "default_params": {
          "num_inference_steps": 8,
          "clip_skip": 2,
          "guidance_scale": 2
        },
        "credit_cost": 0.001
      },
      "GoJourney": {
        "supporting_pipelines": [
          "gojourney",
          "txt2img"
        ],
        "default_params": {},
        "credit_cost": 0.001
      },
      "StickerMaker": {
        "supporting_pipelines": [
          "txt2img"
        ],
        "credit_cost": 0.001
      },
      "FaceToMany": {
        "supporting_pipelines": [
          "img2img"
        ],
        "credit_cost": 0.001
      }
    }
  },
  {
    "_id": "66418841cc48740007156638",
    "name": "ratio-to-size",
    "data": {
      "1:1": [
        1024,
        1024
      ],
      "3:2": [
        1152,
        768
      ],
      "2:3": [
        768,
        1152
      ],
      "19:13": [
        1216,
        832
      ],
      "13:19": [
        832,
        1216
      ],
      "16:9": [
        1360,
        768
      ],
      "9:16": [
        768,
        1360
      ]
    }
  },
  {
    "_id:" "669f7352305c0200075cfef7",
    "name": "tokenizer",
    "data": {
        "Gemma7b": "alpindale/gemma-7b-it",
        "Llama3_70b": "casperhansen/llama-3-70b-instruct-awq"
    }
  }
]
