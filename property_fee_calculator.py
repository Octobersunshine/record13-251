from typing import List, Dict, Tuple


class PropertyFeeCalculator:
    def __init__(self, basic_fee: float, loss_fee: float, households: List[Dict]):
        self.basic_fee = basic_fee
        self.loss_fee = loss_fee
        self.households = households

    @classmethod
    def from_total(cls, total_common_fee: float, basic_ratio: float, households: List[Dict]):
        if not 0 <= basic_ratio <= 1:
            raise ValueError("基础公摊比例必须在 0 到 1 之间")
        basic_fee = total_common_fee * basic_ratio
        loss_fee = total_common_fee - basic_fee
        return cls(basic_fee, loss_fee, households)

    def _validate_inputs(self):
        if self.basic_fee < 0:
            raise ValueError("基础公摊电费不能为负数")
        if self.loss_fee < 0:
            raise ValueError("损耗公摊电费不能为负数")
        if not self.households:
            raise ValueError("住户列表不能为空")
        for h in self.households:
            if "area" not in h or h["area"] <= 0:
                raise ValueError(f"住户 {h.get('id', '未知')} 的面积必须为正数")
            if "occupied" not in h or not isinstance(h["occupied"], bool):
                raise ValueError(f"住户 {h.get('id', '未知')} 的入住状态必须为布尔值")

    def calculate(self) -> Tuple[List[Dict], Dict]:
        self._validate_inputs()

        occupied_households = [h for h in self.households if h["occupied"]]
        total_area = sum(h["area"] for h in self.households)
        total_occupied_area = sum(h["area"] for h in occupied_households)

        if total_area <= 0:
            raise ValueError("所有住户总面积必须大于零")

        results = []
        basic_calculated = 0.0
        loss_calculated = 0.0

        sorted_households = sorted(self.households, key=lambda h: (not h["occupied"], h.get("id", "")))

        last_occupied_idx = None
        for idx, h in enumerate(sorted_households):
            if h["occupied"]:
                last_occupied_idx = idx

        last_idx = len(sorted_households) - 1

        for idx, h in enumerate(sorted_households):
            basic_ratio = h["area"] / total_area
            basic_share = self.basic_fee * basic_ratio

            if idx == last_idx:
                basic_share = self.basic_fee - basic_calculated
            else:
                basic_calculated += basic_share

            if h["occupied"]:
                loss_ratio = h["area"] / total_occupied_area if total_occupied_area > 0 else 0.0
                loss_share = self.loss_fee * loss_ratio
                if idx == last_occupied_idx:
                    loss_share = self.loss_fee - loss_calculated
                else:
                    loss_calculated += loss_share
            else:
                loss_ratio = 0.0
                loss_share = 0.0

            total_fee = basic_share + loss_share
            total_common_fee = self.basic_fee + self.loss_fee
            total_share_ratio = total_fee / total_common_fee if total_common_fee > 0 else 0.0

            results.append({
                "id": h.get("id", f"住户{idx + 1}"),
                "area": h["area"],
                "occupied": h["occupied"],
                "basic_ratio": round(basic_ratio, 6),
                "basic_fee": round(basic_share, 2),
                "loss_ratio": round(loss_ratio, 6),
                "loss_fee": round(loss_share, 2),
                "share_ratio": round(total_share_ratio, 6),
                "fee": round(total_fee, 2),
            })

        summary = {
            "total_common_fee": round(self.basic_fee + self.loss_fee, 2),
            "basic_fee": round(self.basic_fee, 2),
            "loss_fee": round(self.loss_fee, 2),
            "total_households": len(self.households),
            "occupied_count": len(occupied_households),
            "unoccupied_count": len(self.households) - len(occupied_households),
            "total_area": round(total_area, 2),
            "total_occupied_area": round(total_occupied_area, 2),
            "total_calculated_basic": round(sum(r["basic_fee"] for r in results), 2),
            "total_calculated_loss": round(sum(r["loss_fee"] for r in results), 2),
            "total_calculated_fee": round(sum(r["fee"] for r in results), 2),
        }

        return results, summary


def main():
    households = [
        {"id": "101", "area": 80.5, "occupied": True},
        {"id": "102", "area": 95.0, "occupied": True},
        {"id": "201", "area": 120.0, "occupied": False},
        {"id": "202", "area": 85.5, "occupied": True},
        {"id": "301", "area": 110.0, "occupied": True},
    ]

    total_fee = 500.0
    basic_ratio = 0.6

    calculator = PropertyFeeCalculator.from_total(total_fee, basic_ratio, households)
    results, summary = calculator.calculate()

    print("=" * 80)
    print(f"{'物业公摊电费计算结果':^80}")
    print("=" * 80)
    print(f"总公摊电费: ¥{summary['total_common_fee']:.2f}")
    print(f"  ├─ 基础公摊: ¥{summary['basic_fee']:.2f} (占比 {basic_ratio * 100:.0f}%)")
    print(f"  └─ 损耗公摊: ¥{summary['loss_fee']:.2f} (占比 {(1 - basic_ratio) * 100:.0f}%)")
    print(f"住户总数: {summary['total_households']} 户 (入住 {summary['occupied_count']} 户 / 空置 {summary['unoccupied_count']} 户)")
    print(f"总建筑面积: {summary['total_area']:.2f} ㎡  (入住面积: {summary['total_occupied_area']:.2f} ㎡)")
    print("-" * 80)
    print(f"{'房号':<8}{'面积(㎡)':<10}{'状态':<6}{'基础分摊':<12}{'损耗分摊':<12}{'总比例':<10}{'总电费(元)':<12}")
    print("-" * 80)

    for r in results:
        status = "入住" if r["occupied"] else "空置"
        basic_str = f"¥{r['basic_fee']:.2f}"
        loss_str = f"¥{r['loss_fee']:.2f}" if r["occupied"] else "-"
        ratio_str = f"{r['share_ratio'] * 100:.2f}%"
        fee_str = f"¥{r['fee']:.2f}"
        print(f"{r['id']:<8}{r['area']:<10.2f}{status:<6}{basic_str:<12}{loss_str:<12}{ratio_str:<10}{fee_str:<12}")

    print("-" * 80)
    total_basic_str = f"¥{summary['total_calculated_basic']:.2f}"
    total_loss_str = f"¥{summary['total_calculated_loss']:.2f}"
    total_all_str = f"¥{summary['total_calculated_fee']:.2f}"
    print(f"{'合计':<24}{total_basic_str:<12}{total_loss_str:<12}{'':<10}{total_all_str:<12}")
    print("=" * 80)
    print()
    print("说明:")
    print("  1. 基础公摊：所有住户（含空置）按建筑面积比例分摊")
    print("  2. 损耗公摊：仅入住住户按入住面积比例分摊，空置住户无需承担")


if __name__ == "__main__":
    main()
