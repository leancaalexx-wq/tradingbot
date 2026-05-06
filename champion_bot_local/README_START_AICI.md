# Champion Bot - pornire locala pe Windows

Aceasta mapa contine fisiere simple pentru pornirea botului `champion-profile`.

Important:
- Nu pune cheia privata in GitHub.
- Nu trimite cheia privata nimanui.
- Incepe live cu `10 USDC` per trade, nu cu 100.
- Backtestul nu garanteaza profit live.

## 1. Ce trebuie instalat pe calculator

Instaleaza:

1. Python 3.11+  
   https://www.python.org/downloads/

   La instalare bifeaza:
   `Add Python to PATH`

2. Git  
   https://git-scm.com/downloads

3. MetaMask / wallet si cont Polymarket cu USDC.

## 2. Descarca proiectul

Deschide Command Prompt sau PowerShell si ruleaza:

```bat
git clone https://github.com/leancaalexx-wq/tradingbot.git
cd tradingbot
```

## 3. Instaleaza botul

Da dublu click pe:

```text
champion_bot_local\01_install.bat
```

Alternativ, poti folosi si numele descriptiv:

```text
champion_bot_local\install_windows.bat
```

## 4. Test fara bani reali

Da dublu click pe:

```text
champion_bot_local\02_start_paper_champion.bat
```

Alternativ:

```text
champion_bot_local\start_paper_champion.bat
```

Asta porneste botul in paper trading. Nu foloseste bani reali.

## 5. Dashboard

Da dublu click pe:

```text
champion_bot_local\03_start_dashboard.bat
```

Alternativ:

```text
champion_bot_local\start_dashboard.bat
```

Apoi deschide in browser:

```text
http://127.0.0.1:8080
```

## 6. Live cu bani reali

Doar dupa ce ai testat paper mode.

Ai nevoie de:
- `POLYMARKET_PRIVATE_KEY`
- `POLYMARKET_FUNDER_ADDRESS`
- USDC in Polymarket
- approvals / trading setup facute pe Polymarket

Da dublu click pe:

```text
champion_bot_local\04_start_live_champion.bat
```

Alternativ:

```text
champion_bot_local\start_live_champion.bat
```

Fereastra te va intreba:
- private key
- funder/proxy address
- stake per trade

Recomand:

```text
Stake: 10
```

## 7. Cum opresti botul

In fereastra unde ruleaza botul:

```text
CTRL + C
```

## 8. Ce profil foloseste

Profilul champion:

```text
MIN_ENTRY_PRICE=0.50
MAX_ENTRY_PRICE=0.90
MIN_EXPECTED_PROFIT_USDC=0
MIN_PRICE_GAP=0.40
MIN_SECONDS_TO_CLOSE=5
MAX_SECONDS_TO_CLOSE=180
```

Pe scurt: cumpara favorita doar cand diferenta fata de cealalta parte este mare.

