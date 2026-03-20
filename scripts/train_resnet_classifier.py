"""Train a ResNet-18 fingerprint classifier."""
from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Dict, List, Tuple
import random

import torch
from torch import nn
from torch.utils.data import DataLoader, Dataset, random_split
from torchvision import transforms
from torchvision.models import ResNet18_Weights, resnet18
from PIL import Image


CLASS_NAMES = ["arch", "left_loop", "right_loop", "whorl"]


def build_model(num_classes: int = 4) -> nn.Module:
    model = resnet18(weights=ResNet18_Weights.IMAGENET1K_V1)
    old_conv = model.conv1
    new_conv = nn.Conv2d(1, old_conv.out_channels, kernel_size=7, stride=2, padding=3, bias=False)
    with torch.no_grad():
        new_conv.weight.copy_(old_conv.weight.mean(dim=1, keepdim=True))
    model.conv1 = new_conv
    model.fc = nn.Linear(model.fc.in_features, num_classes)
    return model


class FingerprintFolder(Dataset):
    def __init__(
        self,
        root: Path,
        transform: transforms.Compose,
        merge_tented_arch: bool = True,
        max_samples: int = 0,
        max_per_class: int = 0,
        seed: int = 42,
    ) -> None:
        self.samples: List[Tuple[Path, int]] = []
        self.transform = transform
        self.merge_tented_arch = merge_tented_arch
        self.max_samples = max_samples
        self.max_per_class = max_per_class
        self.seed = seed

        if (root / "png_txt").exists():
            self._load_sd04(root / "png_txt")
        else:
            self._load_image_folder(root)

        if not self.samples:
            raise ValueError("No valid samples found. Check dataset path and class folders.")
        self._apply_sampling()

    def _load_image_folder(self, root: Path) -> None:
        class_map: Dict[str, str] = {
            "arch": "arch",
            "left_loop": "left_loop",
            "right_loop": "right_loop",
            "whorl": "whorl",
        }
        if self.merge_tented_arch:
            class_map["tented_arch"] = "arch"

        for cls_dir in root.iterdir():
            if not cls_dir.is_dir():
                continue
            name = cls_dir.name.lower()
            if name not in class_map:
                continue
            mapped = class_map[name]
            target = CLASS_NAMES.index(mapped)
            for path in cls_dir.rglob("*"):
                if path.suffix.lower() not in {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff"}:
                    continue
                self.samples.append((path, target))

    def _load_sd04(self, root: Path) -> None:
        code_map = {
            "A": "arch",
            "L": "left_loop",
            "R": "right_loop",
            "W": "whorl",
            "T": "arch" if self.merge_tented_arch else "tented_arch",
        }
        for txt_path in root.rglob("*.txt"):
            if txt_path.name.startswith("."):
                continue
            png_path = txt_path.with_suffix(".png")
            if not png_path.exists():
                continue
            label_code = None
            with txt_path.open("r", encoding="utf-8", errors="ignore") as fh:
                for line in fh:
                    if "Class:" in line:
                        label_code = line.strip().split("Class:")[-1].strip()
                        break
            if label_code is None or label_code not in code_map:
                continue
            mapped = code_map[label_code]
            if mapped not in CLASS_NAMES:
                continue
            target = CLASS_NAMES.index(mapped)
            self.samples.append((png_path, target))

    def _apply_sampling(self) -> None:
        random.seed(self.seed)
        if self.max_per_class and self.max_per_class > 0:
            per_class: Dict[int, List[Tuple[Path, int]]] = {}
            for path, label in self.samples:
                per_class.setdefault(label, []).append((path, label))
            limited: List[Tuple[Path, int]] = []
            for label, items in per_class.items():
                random.shuffle(items)
                limited.extend(items[: self.max_per_class])
            self.samples = limited
        if self.max_samples and self.max_samples > 0 and len(self.samples) > self.max_samples:
            random.shuffle(self.samples)
            self.samples = self.samples[: self.max_samples]

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, index: int) -> Tuple[torch.Tensor, int]:
        path, target = self.samples[index]
        img = Image.open(path).convert("L")
        return self.transform(img), target


def train(args: argparse.Namespace) -> None:
    device = torch.device("cuda" if torch.cuda.is_available() and not args.cpu else "cpu")
    torch.set_num_threads(args.threads)

    if args.no_augment:
        transform = transforms.Compose(
            [transforms.Resize((args.img_size, args.img_size)), transforms.ToTensor()]
        )
    else:
        transform = transforms.Compose(
            [
                transforms.Resize((args.img_size, args.img_size)),
                transforms.RandomRotation(8),
                transforms.ToTensor(),
            ]
        )

    dataset = FingerprintFolder(
        Path(args.data_dir),
        transform,
        merge_tented_arch=args.merge_tented_arch,
        max_samples=args.max_samples,
        max_per_class=args.max_per_class,
        seed=args.seed,
    )
    val_size = int(len(dataset) * args.val_split)
    train_size = len(dataset) - val_size
    train_set, val_set = random_split(dataset, [train_size, val_size])

    train_loader = DataLoader(
        train_set, batch_size=args.batch_size, shuffle=True, num_workers=args.num_workers
    )
    val_loader = DataLoader(
        val_set, batch_size=args.batch_size, shuffle=False, num_workers=args.num_workers
    )

    model = build_model(num_classes=len(CLASS_NAMES)).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr)
    criterion = nn.CrossEntropyLoss()

    best_acc = 0.0
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    for epoch in range(1, args.epochs + 1):
        model.train()
        running_loss = 0.0
        for images, labels in train_loader:
            images = images.to(device)
            labels = labels.to(device)
            optimizer.zero_grad()
            logits = model(images)
            loss = criterion(logits, labels)
            loss.backward()
            optimizer.step()
            running_loss += loss.item() * images.size(0)

        model.eval()
        correct = 0
        total = 0
        with torch.no_grad():
            for images, labels in val_loader:
                images = images.to(device)
                labels = labels.to(device)
                logits = model(images)
                preds = torch.argmax(logits, dim=1)
                correct += (preds == labels).sum().item()
                total += labels.size(0)

        val_acc = correct / max(total, 1)
        print(f"Epoch {epoch}/{args.epochs}  loss={running_loss/max(train_size,1):.4f}  val_acc={val_acc:.4f}")
        if val_acc >= best_acc:
            best_acc = val_acc
            torch.save(model.state_dict(), output_path)

    print(f"Best validation accuracy: {best_acc:.4f}")
    print(f"Saved weights to {output_path}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", required=True, help="Dataset root with class subfolders.")
    parser.add_argument("--epochs", type=int, default=10)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--lr", type=float, default=1e-4)
    parser.add_argument("--img-size", type=int, default=192)
    parser.add_argument("--val-split", type=float, default=0.2)
    parser.add_argument("--merge-tented-arch", action="store_true")
    parser.add_argument("--output", default="weights/resnet18_fingerprint.pth")
    parser.add_argument("--cpu", action="store_true")
    parser.add_argument("--num-workers", type=int, default=0)
    parser.add_argument("--threads", type=int, default=2)
    parser.add_argument("--max-samples", type=int, default=0)
    parser.add_argument("--max-per-class", type=int, default=0)
    parser.add_argument("--no-augment", action="store_true")
    parser.add_argument("--seed", type=int, default=42)
    return parser.parse_args()


if __name__ == "__main__":
    train(parse_args())
