-- Mipham Quant Desktop — Seed Data
-- Inserted on first run when qd_indicator_codes is empty.

-- Strategy 1: Dual Moving Average Crossover
INSERT OR IGNORE INTO qd_indicator_codes (id, user_id, name, description, category, code, version)
VALUES (1, 1, '双均线交叉 (Dual MA Cross)',
    '当短期均线上穿长期均线时买入，下穿时卖出。经典趋势跟踪策略。',
    'Trend',
    '# @strategy name=双均线交叉
# @param ma_fast int 5 短期均线周期
# @param ma_slow int 20 长期均线周期

def on_init(ctx):
    ctx.param("ma_fast", 5)
    ctx.param("ma_slow", 20)

def on_bar(ctx, bar):
    fast = ctx.param("ma_fast")
    slow = ctx.param("ma_slow")
    bars = ctx.bars(max(slow, 100))
    if len(bars) < slow + 1:
        return
    closes = [b.close for b in bars]
    ma_fast_val = sum(closes[-fast:]) / fast
    ma_slow_val = sum(closes[-slow:]) / slow
    ma_fast_prev = sum(closes[-fast-1:-1]) / fast
    ma_slow_prev = sum(closes[-slow-1:-1]) / slow

    if ma_fast_prev < ma_slow_prev and ma_fast_val >= ma_slow_val:
        ctx.buy(bar.close, ctx.param("amount", 100))
    elif ma_fast_prev > ma_slow_prev and ma_fast_val <= ma_slow_val:
        ctx.sell(bar.close, ctx.param("amount", 100))
', 1);

-- Strategy 2: MACD Signal
INSERT OR IGNORE INTO qd_indicator_codes (id, user_id, name, description, category, code, version)
VALUES (2, 1, 'MACD 信号 (MACD Signal)',
    'MACD金叉买入，死叉卖出。使用EMA12和EMA26计算。',
    'Momentum',
    '# @strategy name=MACD信号
# @param fast int 12 快线周期
# @param slow int 26 慢线周期
# @param signal int 9 信号线周期

def on_init(ctx):
    ctx.param("fast", 12)
    ctx.param("slow", 26)
    ctx.param("signal", 9)

def ema(data, period):
    k = 2.0 / (period + 1)
    result = [data[0]]
    for i in range(1, len(data)):
        result.append(data[i] * k + result[-1] * (1 - k))
    return result

def on_bar(ctx, bar):
    fast_p = ctx.param("fast")
    slow_p = ctx.param("slow")
    sig_p = ctx.param("signal")
    bars = ctx.bars(max(slow_p + sig_p, 200))
    if len(bars) < slow_p + sig_p + 1:
        return
    closes = [b.close for b in bars]
    ema_fast = ema(closes, fast_p)
    ema_slow = ema(closes, slow_p)
    diffs = [f - s for f, s in zip(ema_fast, ema_slow)]
    dea = ema(diffs, sig_p)
    macd = 2 * (diffs[-1] - dea[-1])
    macd_prev = 2 * (diffs[-2] - dea[-2])

    if macd_prev < 0 and macd >= 0:
        ctx.buy(bar.close, ctx.param("amount", 100))
    elif macd_prev > 0 and macd <= 0:
        ctx.sell(bar.close, ctx.param("amount", 100))
', 1);

-- Strategy 3: RSI Oversold/Overbought
INSERT OR IGNORE INTO qd_indicator_codes (id, user_id, name, description, category, code, version)
VALUES (3, 1, 'RSI 超买超卖 (RSI Mean Reversion)',
    'RSI低于30超卖买入，高于70超买卖出。均值回归策略。',
    'Mean Reversion',
    '# @strategy name=RSI超买超卖
# @param period int 14 RSI周期
# @param oversold int 30 超卖阈值
# @param overbought int 70 超买阈值

def on_init(ctx):
    ctx.param("period", 14)
    ctx.param("oversold", 30)
    ctx.param("overbought", 70)

def calc_rsi(closes, period):
    gains = [max(0, closes[i] - closes[i-1]) for i in range(1, len(closes))]
    losses = [max(0, closes[i-1] - closes[i]) for i in range(1, len(closes))]
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    if avg_loss == 0:
        return 100.0
    return 100.0 - (100.0 / (1.0 + avg_gain / avg_loss))

def on_bar(ctx, bar):
    period = ctx.param("period")
    bars = ctx.bars(period + 10)
    if len(bars) < period + 1:
        return
    closes = [b.close for b in bars]
    rsi = calc_rsi(closes, period)
    if rsi < ctx.param("oversold"):
        ctx.buy(bar.close, ctx.param("amount", 100))
    elif rsi > ctx.param("overbought"):
        ctx.sell(bar.close, ctx.param("amount", 100))
', 1);

-- Strategy 4: Bollinger Bands Breakout
INSERT OR IGNORE INTO qd_indicator_codes (id, user_id, name, description, category, code, version)
VALUES (4, 1, '布林带突破 (Bollinger Bands Breakout)',
    '价格突破上轨买入，跌破下轨卖出。波动率突破策略。',
    'Volatility',
    '# @strategy name=布林带突破
# @param period int 20 均线周期
# @param stddev float 2.0 标准差倍数

def on_init(ctx):
    ctx.param("period", 20)
    ctx.param("stddev", 2.0)

def on_bar(ctx, bar):
    period = ctx.param("period")
    bars = ctx.bars(period + 5)
    if len(bars) < period:
        return
    closes = [b.close for b in bars]
    sma = sum(closes[-period:]) / period
    variance = sum((c - sma) ** 2 for c in closes[-period:]) / period
    std = variance ** 0.5
    mult = ctx.param("stddev")
    upper = sma + mult * std
    lower = sma - mult * std

    prev_close = closes[-2] if len(closes) > 1 else closes[-1]
    if prev_close < upper and closes[-1] >= upper:
        ctx.buy(bar.close, ctx.param("amount", 100))
    elif prev_close > lower and closes[-1] <= lower:
        ctx.sell(bar.close, ctx.param("amount", 100))
', 1);

-- Strategy 5: Turtle Trading
INSERT OR IGNORE INTO qd_indicator_codes (id, user_id, name, description, category, code, version)
VALUES (5, 1, '海龟交易 (Turtle Trading)',
    '突破N日高点买入，跌破N日低点卖出。经典趋势跟踪。',
    'Trend',
    '# @strategy name=海龟交易
# @param entry int 20 入场突破周期
# @param exit int 10 离场突破周期

def on_init(ctx):
    ctx.param("entry", 20)
    ctx.param("exit", 10)

def on_bar(ctx, bar):
    entry = ctx.param("entry")
    exit_p = ctx.param("exit")
    bars = ctx.bars(entry + 5)
    if len(bars) < entry:
        return
    highs = [b.high for b in bars]
    lows = [b.low for b in bars]
    entry_high = max(highs[-entry-1:-1])
    exit_low = min(lows[-exit_p-1:-1])

    if bar.close > entry_high:
        ctx.buy(bar.close, ctx.param("amount", 100))
    elif bar.close < exit_low:
        ctx.sell(bar.close, ctx.param("amount", 100))
', 1);

-- Strategy 6: Grid Trading
INSERT OR IGNORE INTO qd_indicator_codes (id, user_id, name, description, category, code, version)
VALUES (6, 1, '网格交易 (Grid Trading)',
    '在价格区间内设置买卖网格，震荡市中低买高卖。',
    'Grid',
    '# @strategy name=网格交易
# @param grid_size float 0.5 网格间距百分比
# @param grid_levels int 5 网格层数

def on_init(ctx):
    ctx.param("grid_size", 0.5)
    ctx.param("grid_levels", 5)
    ctx.param("last_price", 0.0)

def on_bar(ctx, bar):
    size = ctx.param("grid_size") / 100.0
    levels = ctx.param("grid_levels")
    last = ctx.param("last_price")
    if last == 0.0:
        ctx.param("last_price", bar.close)
        return
    if bar.close < last * (1.0 - size):
        ctx.buy(bar.close, ctx.param("amount", 50))
        ctx.param("last_price", bar.close)
    elif bar.close > last * (1.0 + size):
        ctx.sell(bar.close, ctx.param("amount", 50))
        ctx.param("last_price", bar.close)
', 1);

-- Strategy 7: Momentum Timing
INSERT OR IGNORE INTO qd_indicator_codes (id, user_id, name, description, category, code, version)
VALUES (7, 1, '动量择时 (Momentum Timing)',
    '计算N日动量，动量为正买入，为负卖出。',
    'Momentum',
    '# @strategy name=动量择时
# @param period int 10 动量周期

def on_init(ctx):
    ctx.param("period", 10)

def on_bar(ctx, bar):
    period = ctx.param("period")
    bars = ctx.bars(period + 2)
    if len(bars) < period + 1:
        return
    momentum = bar.close - bars[-period-1].close
    if momentum > 0:
        ctx.buy(bar.close, ctx.param("amount", 100))
    elif momentum < 0:
        ctx.sell(bar.close, ctx.param("amount", 100))
', 1);

-- Strategy 8: Volatility Contraction
INSERT OR IGNORE INTO qd_indicator_codes (id, user_id, name, description, category, code, version)
VALUES (8, 1, '波动率收敛 (Volatility Contraction)',
    '当波动率收缩到低点时入场，预期后续突破。',
    'Volatility',
    '# @strategy name=波动率收敛
# @param period int 20 计算周期
# @param threshold float 0.5 波动率阈值

def on_init(ctx):
    ctx.param("period", 20)
    ctx.param("threshold", 0.5)

def on_bar(ctx, bar):
    period = ctx.param("period")
    bars = ctx.bars(period * 2)
    if len(bars) < period * 2:
        return
    highs = [b.high for b in bars[-period:]]
    lows = [b.low for b in bars[-period:]]
    curr_range = max(highs) - min(lows)
    prev_highs = [b.high for b in bars[-2*period:-period]]
    prev_lows = [b.low for b in bars[-2*period:-period]]
    prev_range = max(prev_highs) - min(prev_lows) if prev_highs else curr_range

    if prev_range > 0 and curr_range / prev_range < ctx.param("threshold"):
        ctx.buy(bar.close, ctx.param("amount", 100))
', 1);

-- Strategy 9: OBV Divergence
INSERT OR IGNORE INTO qd_indicator_codes (id, user_id, name, description, category, code, version)
VALUES (9, 1, 'OBV 背离 (OBV Divergence)',
    '价格新低但OBV未创新低 = 看涨背离。量价背离策略。',
    'Volume',
    '# @strategy name=OBV背离
# @param period int 14 比较周期

def on_init(ctx):
    ctx.param("period", 14)
    ctx.param("obv", 0.0)
    ctx.param("obvs", [])

def on_bar(ctx, bar):
    period = ctx.param("period")
    obv = ctx.param("obv")
    if obv == 0:
        ctx.param("obv", bar.volume)
        return
    prev_close = ctx.bars(2)[0].close if len(ctx.bars(2)) > 1 else bar.close
    new_obv = obv + (bar.volume if bar.close > prev_close else (-bar.volume if bar.close < prev_close else 0))
    obvs = ctx.param("obvs")
    obvs.append(new_obv)
    if len(obvs) > period * 2:
        obvs = obvs[-period*2:]
    ctx.param("obvs", obvs)
    ctx.param("obv", new_obv)

    if len(obvs) >= period * 2:
        price_now = bar.close
        price_prev = ctx.bars(period + 1)[0].close
        obv_now = max(obvs[-period:])
        obv_prev = max(obvs[-2*period:-period])
        if price_now < price_prev and obv_now > obv_prev:
            ctx.buy(bar.close, ctx.param("amount", 100))
', 1);

-- Strategy 10: Multi-Factor Composite
INSERT OR IGNORE INTO qd_indicator_codes (id, user_id, name, description, category, code, version)
VALUES (10, 1, '多因子综合 (Multi-Factor Composite)',
    '综合趋势、动量、波动率三个因子打分，分数>0买入，<0卖出。',
    'Composite',
    '# @strategy name=多因子综合

def on_init(ctx):
    ctx.param("trend_weight", 0.4)
    ctx.param("momentum_weight", 0.35)
    ctx.param("volatility_weight", 0.25)

def on_bar(ctx, bar):
    bars = ctx.bars(30)
    if len(bars) < 30:
        return
    closes = [b.close for b in bars]

    ma_short = sum(closes[-5:]) / 5
    ma_long = sum(closes[-20:]) / 20
    trend_score = 1 if ma_short > ma_long else -1

    momentum = closes[-1] - closes[-10]
    momentum_score = 1 if momentum > 0 else -1

    returns = [(closes[i] - closes[i-1]) / closes[i-1] for i in range(1, len(closes))]
    avg_ret = sum(returns[-20:]) / 20
    volatility = (sum((r - avg_ret) ** 2 for r in returns[-20:]) / 20) ** 0.5
    vol_score = -1 if volatility > 0.02 else 1

    composite = (
        trend_score * ctx.param("trend_weight") +
        momentum_score * ctx.param("momentum_weight") +
        vol_score * ctx.param("volatility_weight")
    )

    if composite > 0:
        ctx.buy(bar.close, ctx.param("amount", 100))
    elif composite < 0:
        ctx.sell(bar.close, ctx.param("amount", 100))
', 1);

-- Default watchlist symbols
INSERT OR IGNORE INTO qd_watchlist (user_id, market, symbol, name)
VALUES
    (1, 'Crypto', 'BTC/USDT', 'Bitcoin'),
    (1, 'Crypto', 'ETH/USDT', 'Ethereum'),
    (1, 'Crypto', 'BNB/USDT', 'BNB'),
    (1, 'Crypto', 'SOL/USDT', 'Solana'),
    (1, 'CN', '000300', '沪深300'),
    (1, 'CN', '000016', '上证50'),
    (1, 'US', 'AAPL', 'Apple'),
    (1, 'US', 'TSLA', 'Tesla'),
    (1, 'US', 'SPY', 'SPDR S&P 500'),
    (1, 'US', 'QQQ', 'Invesco QQQ Trust');
