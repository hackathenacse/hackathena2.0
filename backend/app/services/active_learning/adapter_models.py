import hashlib
from typing import Dict, Optional, Tuple
import torch
import torch.nn as nn
import torch.nn.functional as F


def compute_param_checksum(model: nn.Module) -> str:
    """Computes a deterministic SHA-256 fingerprint of all trainable model parameters."""
    hasher = hashlib.sha256()
    for param in model.parameters():
        if param.requires_grad:
            hasher.update(param.detach().cpu().numpy().tobytes())
    return hasher.hexdigest()[:16]


class AuthenticaVisualAdapter(nn.Module):
    """
    Trainable Authentica Visual Adaptation Network.
    
    Architecture:
      Operates on top of the FROZEN EfficientNet-B0 (1280-dim penultimate embedding)
      and fuses capture-quality telemetry (blur, luma, noise, spectral anomaly).
      
      Input: 1280 CNN features + 4 capture telemetry features = 1284 features.
      Hidden: LayerNorm(1284) -> Linear(1284, 64) -> GELU -> Dropout(0.05) -> Linear(64, 2).
      
      Output: 2-class logits [real_logit, fake_logit].
      Target convention:
        - Class 0: REAL / Bonafide
        - Class 1: FAKE / Manipulated
    """

    def __init__(self, in_features: int = 1284, hidden_dim: int = 64):
        super().__init__()
        self.in_features = in_features
        self.hidden_dim = hidden_dim

        self.input_norm = nn.LayerNorm(in_features)
        self.fc1 = nn.Linear(in_features, hidden_dim)
        self.act = nn.GELU()
        self.drop = nn.Dropout(0.05)
        self.fc2 = nn.Linear(hidden_dim, 2)

        # Initialize to produce calibrated near-zero delta initially
        nn.init.xavier_uniform_(self.fc1.weight)
        nn.init.zeros_(self.fc1.bias)
        nn.init.xavier_uniform_(self.fc2.weight, gain=0.1)
        nn.init.zeros_(self.fc2.bias)

    def forward(
        self,
        embeddings: torch.Tensor,
        telemetry: Optional[torch.Tensor] = None
    ) -> torch.Tensor:
        """
        Args:
            embeddings: [batch_size, 1280] penultimate EfficientNet features.
            telemetry: [batch_size, 4] optional normalized [blur, luma, noise, spectral].
        Returns:
            logits: [batch_size, 2] adapted classification logits.
        """
        if embeddings.ndim == 1:
            embeddings = embeddings.unsqueeze(0)

        if telemetry is not None:
            if telemetry.ndim == 1:
                telemetry = telemetry.unsqueeze(0)
            x = torch.cat([embeddings, telemetry], dim=-1)
        else:
            if embeddings.size(-1) == self.in_features:
                x = embeddings
            else:
                # Pad zero telemetry if not provided
                pad_len = self.in_features - embeddings.size(-1)
                zero_telem = torch.zeros(
                    (embeddings.size(0), pad_len),
                    dtype=embeddings.dtype,
                    device=embeddings.device
                )
                x = torch.cat([embeddings, zero_telem], dim=-1)

        norm_x = self.input_norm(x)
        h = self.drop(self.act(self.fc1(norm_x)))
        logits = self.fc2(h)
        return logits

    def count_trainable_parameters(self) -> int:
        return sum(p.numel() for p in self.parameters() if p.requires_grad)

    def get_parameter_checksum(self) -> str:
        return compute_param_checksum(self)


class AuthenticaAudioAdapter(nn.Module):
    """
    Trainable Authentica Audio Adaptation Network.
    
    Architecture:
      Operates on top of FROZEN AASIST graph attention embeddings (160-dim)
      plus acoustic indicators (RMS energy, spectral ratio).
      
      Input: 160 AASIST features + 2 acoustic features = 162 features.
      Hidden: LayerNorm(162) -> Linear(162, 32) -> GELU -> Linear(32, 2).
    """

    def __init__(self, in_features: int = 162, hidden_dim: int = 32):
        super().__init__()
        self.in_features = in_features
        self.input_norm = nn.LayerNorm(in_features)
        self.fc1 = nn.Linear(in_features, hidden_dim)
        self.act = nn.GELU()
        self.fc2 = nn.Linear(hidden_dim, 2)

        nn.init.xavier_uniform_(self.fc1.weight)
        nn.init.zeros_(self.fc1.bias)
        nn.init.xavier_uniform_(self.fc2.weight, gain=0.1)
        nn.init.zeros_(self.fc2.bias)

    def forward(
        self,
        embeddings: torch.Tensor,
        acoustic_meta: Optional[torch.Tensor] = None
    ) -> torch.Tensor:
        if embeddings.ndim == 1:
            embeddings = embeddings.unsqueeze(0)

        if acoustic_meta is not None:
            if acoustic_meta.ndim == 1:
                acoustic_meta = acoustic_meta.unsqueeze(0)
            x = torch.cat([embeddings, acoustic_meta], dim=-1)
        else:
            if embeddings.size(-1) == self.in_features:
                x = embeddings
            else:
                pad_len = self.in_features - embeddings.size(-1)
                zero_meta = torch.zeros(
                    (embeddings.size(0), pad_len),
                    dtype=embeddings.dtype,
                    device=embeddings.device
                )
                x = torch.cat([embeddings, zero_meta], dim=-1)

        norm_x = self.input_norm(x)
        h = self.act(self.fc1(norm_x))
        return self.fc2(h)

    def count_trainable_parameters(self) -> int:
        return sum(p.numel() for p in self.parameters() if p.requires_grad)

    def get_parameter_checksum(self) -> str:
        return compute_param_checksum(self)

