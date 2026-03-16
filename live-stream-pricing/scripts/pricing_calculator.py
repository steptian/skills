#!/usr/bin/env python3
"""
直播电商定价计算器

使用方式：
  # 正向定价（成本 → 售价）
  python pricing_calculator.py --cost 13.5 --target-margin 15

  # 反向评估（售价 → 毛利率）
  python pricing_calculator.py --price 39.8 --cost 13.5 --mode eval

  # 回本点分析（含固定成本）
  python pricing_calculator.py --cost 13.5 --price 39.9 --mode eval --fixed-cost 4500

  # 自定义参数
  python pricing_calculator.py --cost 20 --target-margin 20 --commission 30 --return-rate 15

  # 批量定价
  python pricing_calculator.py --batch "8.5,12,18.5,25" --target-margin 15

参数说明：
  --cost           进货成本（元）
  --price          售价（元），反向评估模式必需
  --target-margin  目标净销售毛利率（%），正向定价模式必需
  --mode           模式：pricing（定价，默认）或 eval（评估）
  --fixed-cost     固定成本（元），如坑位费+质检费，用于回本点计算
  --commission     直播间提成比例（%，默认 30）
  --shipping       发货运费+打包（元/单，默认 4）
  --return-rate    退货率（%，默认 20）
  --return-shipping 退货运费险（元/单，默认 4）
  --platform-fee   平台技术服务费（%，默认 6）
  --vat            增值税（%，默认 1）
  --resale         退货是否可二次销售：yes（默认）或 no
  --batch          批量定价，逗号分隔的成本列表
"""

import argparse
import json
import sys
from dataclasses import dataclass, asdict
from typing import Optional, List


@dataclass
class PricingParams:
    """定价参数"""
    cost: float  # 进货成本
    commission_rate: float  # 提成比例（小数）
    shipping: float  # 发货运费
    return_rate: float  # 退货率（小数）
    return_shipping: float  # 退货运费险
    platform_fee_rate: float  # 平台技术服务费（小数）
    vat_rate: float  # 增值税（小数）
    can_resale: bool  # 退货可二次销售


@dataclass
class PricingResult:
    """定价结果"""
    scenario: str  # 场景名称
    price: float  # 建议售价
    net_margin: float  # 净毛利率（小数）
    profit_per_unit: float  # 每单毛利
    effective_orders: int  # 有效订单数（按100单基准）
    total_revenue: float  # 有效营收
    total_cost: float  # 总成本
    total_profit: float  # 总毛利
    details: dict  # 成本明细


def calculate_price(params: PricingParams, target_margin: float) -> float:
    """
    正向定价：计算建议售价

    公式（按100单发货基准）：
    有效订单 = 100 × (1 - 退货率)
    X = (进货成本 × 有效订单 + 发货运费 × 100 + 退货运费 × 退货数)
        ÷ (有效订单 × (1 - 提成率 - 平台费率 - 目标毛利率))
    """
    effective_orders = 100 * (1 - params.return_rate)
    return_orders = 100 * params.return_rate

    # 进货成本：可二次销售只计有效订单，不可二次销售计全部
    if params.can_resale:
        cost_multiplier = effective_orders
    else:
        cost_multiplier = 100

    numerator = (
        params.cost * cost_multiplier +
        params.shipping * 100 +
        params.return_shipping * return_orders
    )

    denominator = effective_orders * (
        1 - params.commission_rate - params.platform_fee_rate - params.vat_rate - target_margin
    )

    if denominator <= 0:
        return float('inf')  # 无法达成目标毛利率

    return numerator / denominator


def calculate_margin(params: PricingParams, price: float) -> float:
    """
    反向评估：计算实际净毛利率

    公式：
    净毛利率 = (有效营收 - 总成本) ÷ 有效营收
    """
    result = evaluate_price(params, price)
    return result.net_margin


def evaluate_price(params: PricingParams, price: float) -> PricingResult:
    """
    评估给定售价的各项指标
    """
    effective_orders = 100 * (1 - params.return_rate)
    return_orders = 100 * params.return_rate

    # 有效营收
    total_revenue = price * effective_orders

    # 各项成本
    if params.can_resale:
        cost_of_goods = params.cost * effective_orders
    else:
        cost_of_goods = params.cost * 100

    shipping_cost = params.shipping * 100
    return_shipping_cost = params.return_shipping * return_orders
    commission = total_revenue * params.commission_rate
    platform_fee = total_revenue * params.platform_fee_rate
    vat = total_revenue * params.vat_rate

    total_cost = (
        cost_of_goods +
        shipping_cost +
        return_shipping_cost +
        commission +
        platform_fee +
        vat
    )

    total_profit = total_revenue - total_cost
    net_margin = total_profit / total_revenue if total_revenue > 0 else 0
    profit_per_unit = total_profit / effective_orders if effective_orders > 0 else 0

    return PricingResult(
        scenario="当前参数",
        price=price,
        net_margin=net_margin,
        profit_per_unit=profit_per_unit,
        effective_orders=int(effective_orders),
        total_revenue=round(total_revenue, 2),
        total_cost=round(total_cost, 2),
        total_profit=round(total_profit, 2),
        details={
            "cost_of_goods": round(cost_of_goods, 2),
            "shipping_cost": round(shipping_cost, 2),
            "return_shipping_cost": round(return_shipping_cost, 2),
            "commission": round(commission, 2),
            "platform_fee": round(platform_fee, 2),
            "vat": round(vat, 2),
        }
    )


def generate_scenarios(params: PricingParams, target_margin: Optional[float] = None,
                       price: Optional[float] = None) -> List[PricingResult]:
    """
    生成多种场景的计算结果
    """
    scenarios = []

    # 场景1：无退货
    params_no_return = PricingParams(
        cost=params.cost,
        commission_rate=params.commission_rate,
        shipping=params.shipping,
        return_rate=0,
        return_shipping=0,
        platform_fee_rate=0,
        vat_rate=params.vat_rate,
        can_resale=True
    )

    if target_margin is not None:
        p1 = calculate_price(params_no_return, target_margin)
        r1 = evaluate_price(params_no_return, p1)
        r1.scenario = "无退货（100%确认收货）"
        scenarios.append(r1)

    # 场景2：当前退货率
    if target_margin is not None:
        p2 = calculate_price(params, target_margin)
        r2 = evaluate_price(params, p2)
        r2.scenario = f"退货率{int(params.return_rate*100)}%（行业常态）"
        scenarios.append(r2)

    # 场景3：叠加平台费
    if params.platform_fee_rate == 0 and target_margin is not None:
        params_with_fee = PricingParams(
            cost=params.cost,
            commission_rate=params.commission_rate,
            shipping=params.shipping,
            return_rate=params.return_rate,
            return_shipping=params.return_shipping,
            platform_fee_rate=0.02,
            vat_rate=params.vat_rate,
            can_resale=params.can_resale
        )
        p3 = calculate_price(params_with_fee, target_margin)
        r3 = evaluate_price(params_with_fee, p3)
        r3.scenario = "叠加平台费2%"
        scenarios.append(r3)

    # 场景4：退货不可二次销售
    if params.can_resale and target_margin is not None:
        params_no_resale = PricingParams(
            cost=params.cost,
            commission_rate=params.commission_rate,
            shipping=params.shipping,
            return_rate=params.return_rate,
            return_shipping=params.return_shipping,
            platform_fee_rate=params.platform_fee_rate,
            vat_rate=params.vat_rate,
            can_resale=False
        )
        p4 = calculate_price(params_no_resale, target_margin)
        r4 = evaluate_price(params_no_resale, p4)
        r4.scenario = "退货不可二次销售"
        scenarios.append(r4)

    # 反向评估场景
    if price is not None:
        r_eval = evaluate_price(params, price)
        r_eval.scenario = "当前定价评估"
        scenarios.append(r_eval)

    return scenarios


def calculate_break_even(params: PricingParams, price: float, fixed_cost: float) -> dict:
    """
    计算回本点

    返回：
    - profit_per_unit: 每单净毛利
    - confirmed_orders: 需要的确认收货订单数
    - shipped_orders: 需要的发货订单数（考虑退货）
    - scenarios: 不同销量下的定价建议
    """
    result = evaluate_price(params, price)
    profit_per_unit = result.profit_per_unit

    if profit_per_unit <= 0:
        return {
            "profit_per_unit": profit_per_unit,
            "confirmed_orders": float('inf'),
            "shipped_orders": float('inf'),
            "scenarios": [],
            "warning": "当前定价亏损，无法回本"
        }

    # 回本需要的确认收货订单数
    confirmed_orders = fixed_cost / profit_per_unit
    # 考虑退货率，需要的发货订单数
    shipped_orders = confirmed_orders / (1 - params.return_rate)

    # 不同销量场景下的定价建议
    scenarios = []
    for expected_shipped in [100, 200, 500, 1000]:
        for target_margin in [0.15, 0.20]:
            effective = expected_shipped * (1 - params.return_rate)

            # 计算需要的价格（含固定成本分摊）
            if params.can_resale:
                cost_multiplier = effective
            else:
                cost_multiplier = expected_shipped

            numerator = (
                params.cost * cost_multiplier +
                params.shipping * expected_shipped +
                params.return_shipping * expected_shipped * params.return_rate +
                fixed_cost
            )
            denominator = effective * (
                1 - params.commission_rate - params.platform_fee_rate - params.vat_rate - target_margin
            )

            if denominator > 0:
                new_price = numerator / denominator
                if 0 < new_price < 500:
                    total_revenue = new_price * effective
                    total_profit = total_revenue * target_margin
                    scenarios.append({
                        "shipped_orders": expected_shipped,
                        "target_margin": int(target_margin * 100),
                        "suggested_price": round(new_price, 1),
                        "total_profit": round(total_profit)
                    })

    return {
        "profit_per_unit": round(profit_per_unit, 2),
        "confirmed_orders": round(confirmed_orders),
        "shipped_orders": round(shipped_orders),
        "scenarios": scenarios
    }


def batch_pricing(costs: List[float], target_margin: float,
                  params: PricingParams) -> List[dict]:
    """批量定价"""
    results = []
    for cost in costs:
        p = PricingParams(
            cost=cost,
            commission_rate=params.commission_rate,
            shipping=params.shipping,
            return_rate=params.return_rate,
            return_shipping=params.return_shipping,
            platform_fee_rate=params.platform_fee_rate,
            vat_rate=params.vat_rate,
            can_resale=params.can_resale
        )
        price = calculate_price(p, target_margin)
        result = evaluate_price(p, price)
        results.append({
            "cost": cost,
            "price": round(price, 2),
            "net_margin": round(result.net_margin * 100, 2),
            "profit_per_unit": round(result.profit_per_unit, 2)
        })
    return results


def main():
    parser = argparse.ArgumentParser(description="直播电商定价计算器")
    parser.add_argument("--cost", type=float, help="进货成本（元）")
    parser.add_argument("--price", type=float, help="售价（元）")
    parser.add_argument("--target-margin", type=float, help="目标净毛利率（%）")
    parser.add_argument("--mode", choices=["pricing", "eval"], default="pricing",
                        help="模式：pricing（定价）或 eval（评估）")
    parser.add_argument("--commission", type=float, default=30,
                        help="直播间提成比例（%，默认30）")
    parser.add_argument("--shipping", type=float, default=4,
                        help="发货运费+打包（元/单，默认4）")
    parser.add_argument("--return-rate", type=float, default=20,
                        help="退货率（%，默认20）")
    parser.add_argument("--return-shipping", type=float, default=4,
                        help="退货运费险（元/单，默认4）")
    parser.add_argument("--platform-fee", type=float, default=6,
                        help="平台技术服务费（%，默认6）")
    parser.add_argument("--vat", type=float, default=1,
                        help="增值税（%，默认1）")
    parser.add_argument("--resale", choices=["yes", "no"], default="yes",
                        help="退货是否可二次销售（默认yes）")
    parser.add_argument("--batch", type=str, help="批量定价，逗号分隔的成本列表")
    parser.add_argument("--fixed-cost", type=float, default=0,
                        help="固定成本（元），如坑位费+质检费，用于回本点计算")
    parser.add_argument("--json", action="store_true", help="输出JSON格式")

    args = parser.parse_args()

    # 构建参数
    params = PricingParams(
        cost=args.cost or 0,
        commission_rate=args.commission / 100,
        shipping=args.shipping,
        return_rate=args.return_rate / 100,
        return_shipping=args.return_shipping,
        platform_fee_rate=args.platform_fee / 100,
        vat_rate=args.vat / 100,
        can_resale=(args.resale == "yes")
    )

    output = {"params": asdict(params)}

    # 批量定价模式
    if args.batch:
        costs = [float(x.strip()) for x in args.batch.split(",")]
        target_margin = (args.target_margin or 15) / 100
        output["mode"] = "batch"
        output["target_margin"] = target_margin
        output["results"] = batch_pricing(costs, target_margin, params)

    # 反向评估模式
    elif args.mode == "eval" and args.price and args.cost:
        output["mode"] = "eval"
        output["price"] = args.price
        scenarios = generate_scenarios(params, price=args.price)
        output["scenarios"] = [asdict(s) for s in scenarios]

        # 回本点分析
        if args.fixed_cost and args.fixed_cost > 0:
            output["fixed_cost"] = args.fixed_cost
            output["break_even"] = calculate_break_even(params, args.price, args.fixed_cost)

    # 正向定价模式
    elif args.cost and args.target_margin:
        output["mode"] = "pricing"
        output["target_margin"] = args.target_margin / 100
        scenarios = generate_scenarios(params, target_margin=args.target_margin / 100)
        output["scenarios"] = [asdict(s) for s in scenarios]

    else:
        parser.print_help()
        sys.exit(1)

    if args.json:
        print(json.dumps(output, ensure_ascii=False, indent=2))
    else:
        # 人类可读输出
        print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
