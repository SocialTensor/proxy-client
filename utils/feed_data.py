VALIDATORS_FEED = [
    {
        "_id": "[validator_id]",
        "generate_endpoint": "http://[validator_addr]/validator_proxy",
        "is_active": True,
        "counter": {"2024-06-19": {"success": 0, "failure": 0}},
    }
]

AUTH_KEYS_FEED = [
    {"_id": "[auth_key]", "request_count": 0, "credit": 5, "email": "", "password": ""}
]

MODEL_CONFIG_FEED = [
    {
        "_id": "[model_config]",
        "name": "model_list",
        "data": {
            "JuggernautXL": {
                "supporting_pipelines": ["txt2img"],
                "default_params": {
                    "num_inference_steps": 30,
                    "clip_skip": 2,
                    "guidance_scale": 7,
                },
            },
            "AnimeV3": {
                "supporting_pipelines": ["txt2img"],
                "default_params": {
                    "num_inference_steps": 25,
                    "clip_skip": 2,
                    "guidance_scale": 7,
                },
            },
            "RealitiesEdgeXL": {
                "supporting_pipelines": ["txt2img", "controlnet"],
                "default_params": {
                    "num_inference_steps": 8,
                    "clip_skip": 2,
                    "guidance_scale": 2,
                },
            },
            "DreamShaperXL": {
                "supporting_pipelines": ["txt2img", "instantid", "img2img"],
                "default_params": {
                    "num_inference_steps": 8,
                    "clip_skip": 2,
                    "guidance_scale": 2,
                },
            },
            "GoJourney": {
                "supporting_pipelines": ["gojourney", "txt2img"],
                "default_params": {},
            },
            "StickerMaker": {"supporting_pipelines": ["txt2img"]},
            "FaceToMany": {"supporting_pipelines": ["img2img"]},
            "DallE": {"supporting_pipelines": ["txt2img"]},
            "Gemma7b": {"supporting_pipelines": ["text_generation"]},
            "Llama3_70b": {"supporting_pipelines": ["text_generation"]},
            "FluxSchnell": {"supporting_pipelines": ["txt2img"]},
            "Kolors": {"supporting_pipelines": ["txt2img", "controlnet", "ip_adapter"]},
            "SUPIR": {"supporting_pipelines": ["upscale"]},
            "OpenGeneral": {"supporting_pipelines": ["txt2img"]},
            "Pixtral_12b": {"supporting_pipelines": ["visual_question_answering"]},
        },
    },
    {
        "_id": "[ratio-config]",
        "name": "ratio-to-size",
        "data": {
            "1:1": [1024, 1024],
            "3:2": [1152, 768],
            "2:3": [768, 1152],
            "19:13": [1216, 832],
            "13:19": [832, 1216],
            "16:9": [1360, 768],
            "9:16": [768, 1360],
        },
    },
    {
        "_id": "[tokenizer]",
        "name": "tokenizer",
        "data": {
            "Gemma7b": "alpindale/gemma-7b-it",
            "Llama3_70b": "casperhansen/llama-3-70b-instruct-awq",
        },
    },
]
