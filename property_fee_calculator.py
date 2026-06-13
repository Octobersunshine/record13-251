from typing import List, Dict, Tuple


class PropertyFeeCalculator:
    def __init__(self, total_common_fee: float, households: List[Dict]):
        self.total_common_fee = total_common_fee
        self.households = households

    def _validate_inputs(self):
        if self.total_common_fee < 0:
            raise ValueError("总公摊电费不能为负数")
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

        if not occupied_households:
            raise ValueError("没有入住的住户，无法分摊电费")

        total_occupied_area = sum(h["area"] for h in occupied_households)

        results = []
        total_calculated = 0.0

        for idx, h in enumerate(occupied_households):
            share_ratio = h["area"] / total_occupied_area
            fee = self.total_common_fee * share_ratio

            if idx == len(occupied_households) - 1:
                fee = self.total_common_fee - total_calculated
            else:
                total_calculated += fee

            results.append({
                "id": h.get("id", f"住户{idx + 1}"),
                "area": h["area"],
                "occupied": True,
                "share_ratio": round(share_ratio, 6),
                "fee": round(fee, 2),
            })

        unoccupied_households = [h for h in self.households if not h["occupied"]]
        for h in unoccupied_households:
            results.append({
                "id": h.get("id", "未知住户"),
                "area": h["area"],
                "occupied": False,
                "share_ratio": 0.0,
                "fee": 0.0,
            })

        summary = {
            "total_common_fee": round(self.total_common_fee, 2),
            "total_households": len(self.households),
            "occupied_count": len(occupied_households),
            "total_occupied_area": round(total_occupied_area, 2),
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

    calculator = PropertyFeeCalculator(total_fee, households)
    results, summary = calculator.calculate()

    print("=" * 60)
    print(f"{'物业公摊电费计算结果':^60}")
    print("=" * 60)
    print(f"总公摊电费: ¥{summary['total_common_fee']:.2f}")
    print(f"住户总数: {summary['total_households']} 户")
    print(f"入住户数: {summary['occupied_count']} 户")
    print(f"入住总面积: {summary['total_occupied_area']:.2f} ㎡")
    print("-" * 60)
    print(f"{'房号':<10}{'面积(㎡)':<12}{'状态':<8}{'分摊比例':<12}{'分摊电费(元)':<14}")
    print("-" * 60)

    for r in results:
        status = "入住" if r["occupied"] else "未入住"
        ratio = f"{r['share_ratio'] * 100:.2f}%" if r["occupied"] else "-"
        fee = f"¥{r['fee']:.2f}" if r["occupied"] else "-"
        print(f"{r['id']:<10}{r['area']:<12.2f}{status:<8}{ratio:<12}{fee:<14}")

    print("-" * 60)
    total_str = f"¥{summary['total_calculated_fee']:.2f}"
    print(f"{'合计':<30}{total_str:>20}")
    print("=" * 60)


if __name__ == "__main__":
    main()
