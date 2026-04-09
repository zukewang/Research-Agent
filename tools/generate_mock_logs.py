# tools/generate_mock_logs.py
import os
from pathlib import Path
from datetime import datetime, timedelta
import random

def generate_mock_logs(log_dir = Path(__file__).parent.parent / "experiments"):
    log_dir = Path(log_dir).expanduser()
    log_dir.mkdir(parents=True, exist_ok=True)

    # 定义实验模板
    experiments = [
        {
            "name": "vit_baseline",
            "paper": "Vision Transformer",
            "epochs": 50,
            "success": True
        },
        {
            "name": "diffusion_ablation",
            "paper": "Denoising Diffusion Probabilistic Models",
            "epochs": 100,
            "success": False  # 模拟失败
        },
        {
            "name": "llm_finetune",
            "paper": "Large Language Model Fine-tuning",
            "epochs": 200,
            "success": "running"  # 模拟运行中
        }
    ]

    for exp in experiments:
        filename = f"{exp['name']}_{datetime.now().strftime('%Y%m%d')}.log"
        filepath = log_dir / filename

        lines = []
        lines.append(f"[{datetime.now().isoformat()}] Starting experiment: {exp['paper']}\n")
        lines.append(f"Config: epochs={exp['epochs']}, lr=1e-4, batch_size=32\n")

        if exp["success"] == "running":
            # 模拟正在训练（最后没有完成标志）
            for epoch in range(1, min(10, exp["epochs"])+1):
                loss = round(2.0 - (epoch * 0.05), 3)
                acc = round(0.1 + (epoch * 0.02), 3)
                lines.append(f"Epoch {epoch}/{exp['epochs']}: loss={loss}, acc={acc}\n")
            # 不写 "Training completed"

        elif exp["success"] is False:
            # 模拟失败
            for epoch in range(1, 5):
                loss = round(2.0 - (epoch * 0.05), 3)
                lines.append(f"Epoch {epoch}: loss={loss}\n")
            lines.append("Error: CUDA out of memory!\n")
            lines.append("Traceback (most recent call last):\n")
            lines.append("  File \"train.py\", line 120, in <module>\n")

        else:
            # 成功完成
            for epoch in range(1, exp["epochs"]+1):
                loss = round(2.0 - (epoch * 0.03), 3)
                acc = round(0.1 + (epoch * 0.015), 3)
                if epoch % 10 == 0 or epoch == exp["epochs"]:
                    lines.append(f"Epoch {epoch}/{exp['epochs']}: loss={loss}, acc={acc}\n")
            lines.append("Training completed.\n")
            final_acc = round(0.1 + (exp["epochs"] * 0.015), 3)
            lines.append(f"Final accuracy: {final_acc:.1%}\n")

        with open(filepath, 'w', encoding='utf-8') as f:
            f.writelines(lines)

        print(f"✅ Generated: {filepath}")

    print(f"\n🎉 Mock logs created in: {log_dir}")
    print("You can now test your ExperimentStatusTool!")

if __name__ == "__main__":
    generate_mock_logs()