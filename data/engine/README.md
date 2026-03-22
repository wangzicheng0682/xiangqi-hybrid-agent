# Chess Engine Directory

Place your Pikafish executable here.

## Download

Download from: https://github.com/official-pikafish/Pikafish/releases

### Linux
```bash
wget https://github.com/official-pikafish/Pikafish/releases/download/v2024.08.05/pikafish-bmi2-linux.tar.bz2
tar -xjf pikafish-bmi2-linux.tar.bz2
chmod +x pikafish
rm pikafish-bmi2-linux.tar.bz2
```

### macOS (Apple Silicon)
```bash
wget https://github.com/official-pikafish/Pikafish/releases/download/v2024.08.05/pikafish-bmi2-apple.tar.bz2
tar -xjf pikafish-bmi2-apple.tar.bz2
chmod +x pikafish
rm pikafish-bmi2-apple.tar.bz2
```

### Windows
Download `pikafish-bmi2-win.zip` and extract `pikafish.exe` here.

## Verification

```bash
./pikafish
uci
# Expected: "id name Pikafish..."
quit
```

## Configuration

Update `config/settings.yaml`:
```yaml
engine:
  path: "data/engine/pikafish"
```
