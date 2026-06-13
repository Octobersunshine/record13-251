from typing import List, Dict, Tuple, Optional


class PropertyFeeCalculator:
    def __init__(self, basic_fee: float, loss_fee: float, households: List[Dict], floor_coefficients: Optional[Dict[int, float]] = None):
        self.basic_fee = basic_fee
        self.loss_fee = loss_fee
        self.households = households
        self.floor_coefficients = floor_coefficients or {}

    @classmethod
    def from_total(cls, total_common_fee: float, basic_ratio: float, households: List[Dict], floor_coefficients: Optional[Dict[int, float]] = None):
        if not 0 <= basic_ratio <= 1:
            raise ValueError("基础公摊比例必须在 0 到 1 之间")
        basic_fee = total_common_fee * basic_ratio
        loss_fee = total_common_fee - basic_fee
        return cls(basic_fee, loss_fee, households, floor_coefficients)

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
        for floor, coeff in self.floor_coefficients.items():
            if coeff <= 0:
                raise ValueError(f"楼层 {floor} 的系数必须为正数，当前为 {coeff}")

    def _get_floor_coefficient(self, household: Dict) -> float:
        floor = household.get("floor")
        if floor is not None and floor in self.floor_coefficients:
            return self.floor_coefficients[floor]
        return 1.0

    def calculate(self) -> Tuple[List[Dict], Dict]:
        self._validate_inputs()

        occupied_households = [h for h in self.households if h["occupied"]]

        household_weighted = []
        for h in self.households:
            coeff = self._get_floor_coefficient(h)
            weighted_area = h["area"] * coeff
            household_weighted.append((h, coeff, weighted_area))

        total_weighted_area = sum(wa for _, _, wa in household_weighted)
        total_occupied_weighted_area = sum(
            wa for h, _, wa in household_weighted if h["occupied"]
        )

        if total_weighted_area <= 0:
            raise ValueError("所有住户加权总面积必须大于零")
        if total_occupied_weighted_area <= 0 and self.loss_fee > 0:
            raise ValueError("没有入住的住户，无法分摊损耗电费")

        results = []
        basic_calculated = 0.0
        loss_calculated = 0.0

        sorted_items = sorted(
            household_weighted,
            key=lambda item: (not item[0]["occupied"], item[0].get("id", "")),
        )

        last_occupied_idx = None
        for idx, (h, _, _) in enumerate(sorted_items):
            if h["occupied"]:
                last_occupied_idx = idx

        last_idx = len(sorted_items) - 1
        total_common_fee = self.basic_fee + self.loss_fee

        for idx, (h, coeff, weighted_area) in enumerate(sorted_items):
            basic_ratio = weighted_area / total_weighted_area
            basic_share = self.basic_fee * basic_ratio

            if idx == last_idx:
                basic_share = self.basic_fee - basic_calculated
            else:
                basic_calculated += basic_share

            if h["occupied"]:
                loss_ratio = weighted_area / total_occupied_weighted_area if total_occupied_weighted_area > 0 else 0.0
                loss_share = self.loss_fee * loss_ratio
                if idx == last_occupied_idx:
                    loss_share = self.loss_fee - loss_calculated
                else:
                    loss_calculated += loss_share
            else:
                loss_ratio = 0.0
                loss_share = 0.0

            total_fee = basic_share + loss_share
            total_share_ratio = total_fee / total_common_fee if total_common_fee > 0 else 0.0

            results.append({
                "id": h.get("id", f"住户{idx + 1}"),
                "area": h["area"],
                "floor": h.get("floor"),
                "floor_coefficient": coeff,
                "weighted_area": round(weighted_area, 2),
                "occupied": h["occupied"],
                "basic_ratio": round(basic_ratio, 6),
                "basic_fee": round(basic_share, 2),
                "loss_ratio": round(loss_ratio, 6),
                "loss_fee": round(loss_share, 2),
                "share_ratio": round(total_share_ratio, 6),
                "fee": round(total_fee, 2),
            })

        total_fee_sum = sum(r["fee"] for r in results)
        total_basic_sum = sum(r["basic_fee"] for r in results)
        total_loss_sum = sum(r["loss_fee"] for r in results)

        fee_error = round(total_common_fee - total_fee_sum, 2)
        basic_error = round(self.basic_fee - total_basic_sum, 2)
        loss_error = round(self.loss_fee - total_loss_sum, 2)

        if fee_error != 0 or basic_error != 0 or loss_error != 0:
            results[last_idx]["fee"] = round(results[last_idx]["fee"] + fee_error, 2)
            results[last_idx]["basic_fee"] = round(results[last_idx]["basic_fee"] + basic_error, 2)
            results[last_idx]["loss_fee"] = round(results[last_idx]["loss_fee"] + loss_error, 2)

        total_area = sum(h["area"] for h in self.households)
        total_occupied_area = sum(h["area"] for h in occupied_households)

        summary = {
            "total_common_fee": round(self.basic_fee + self.loss_fee, 2),
            "basic_fee": round(self.basic_fee, 2),
            "loss_fee": round(self.loss_fee, 2),
            "total_households": len(self.households),
            "occupied_count": len(occupied_households),
            "unoccupied_count": len(self.households) - len(occupied_households),
            "total_area": round(total_area, 2),
            "total_occupied_area": round(total_occupied_area, 2),
            "total_weighted_area": round(total_weighted_area, 2),
            "total_occupied_weighted_area": round(total_occupied_weighted_area, 2),
            "total_calculated_basic": round(sum(r["basic_fee"] for r in results), 2),
            "total_calculated_loss": round(sum(r["loss_fee"] for r in results), 2),
            "total_calculated_fee": round(sum(r["fee"] for r in results), 2),
        }

        return results, summary


def main():
    households = [
        {"id": "101", "area": 80.5, "occupied": True, "floor": 1},
        {"id": "102", "area": 95.0, "occupied": True, "floor": 1},
        {"id": "201", "area": 120.0, "occupied": False, "floor": 2},
        {"id": "202", "area": 85.5, "occupied": True, "floor": 2},
        {"id": "301", "area": 110.0, "occupied": True, "floor": 3},
    ]

    floor_coefficients = {1: 1.0, 2: 1.1, 3: 1.2}

    total_fee = 500.0
    basic_ratio = 0.6

    calculator = PropertyFeeCalculator.from_total(total_fee, basic_ratio, households, floor_coefficients)
    results, summary = calculator.calculate()

    print("=" * 90)
    print(f"{'物业公摊电费计算结果':^90}")
    print("=" * 90)
    print(f"总公摊电费: ¥{summary['total_common_fee']:.2f}")
    print(f"  ├─ 基础公摊: ¥{summary['basic_fee']:.2f} (占比 {basic_ratio * 100:.0f}%)")
    print(f"  └─ 损耗公摊: ¥{summary['loss_fee']:.2f} (占比 {(1 - basic_ratio) * 100:.0f}%)")
    print(f"住户总数: {summary['total_households']} 户 (入住 {summary['occupied_count']} 户 / 空置 {summary['unoccupied_count']} 户)")
    print(f"总建筑面积: {summary['total_area']:.2f} ㎡  (加权面积: {summary['total_weighted_area']:.2f} ㎡)")
    print(f"入住面积: {summary['total_occupied_area']:.2f} ㎡  (加权面积: {summary['total_occupied_weighted_area']:.2f} ㎡)")
    print("-" * 90)
    print(f"{'房号':<8}{'楼层':<6}{'面积(㎡)':<10}{'系数':<6}{'加权面积':<10}{'状态':<6}{'基础分摊':<12}{'损耗分摊':<12}{'总比例':<10}{'总电费(元)':<12}")
    print("-" * 90)

    for r in results:
        status = "入住" if r["occupied"] else "空置"
        floor_str = str(r["floor"]) if r["floor"] is not None else "-"
        coeff_str = f"{r['floor_coefficient']:.1f}"
        basic_str = f"¥{r['basic_fee']:.2f}"
        loss_str = f"¥{r['loss_fee']:.2f}" if r["occupied"] else "-"
        ratio_str = f"{r['share_ratio'] * 100:.2f}%"
        fee_str = f"¥{r['fee']:.2f}"
        print(f"{r['id']:<8}{floor_str:<6}{r['area']:<10.2f}{coeff_str:<6}{r['weighted_area']:<10.2f}{status:<6}{basic_str:<12}{loss_str:<12}{ratio_str:<10}{fee_str:<12}")

    print("-" * 90)
    total_basic_str = f"¥{summary['total_calculated_basic']:.2f}"
    total_loss_str = f"¥{summary['total_calculated_loss']:.2f}"
    total_all_str = f"¥{summary['total_calculated_fee']:.2f}"
    print(f"{'合计':<40}{total_basic_str:<12}{total_loss_str:<12}{'':<10}{total_all_str:<12}")
    print("=" * 90)
    print()
    print("说明:")
    print("  1. 基础公摊：所有住户（含空置）按加权面积比例分摊")
    print("  2. 损耗公摊：仅入住住户按加权面积比例分摊，空置住户无需承担")
    print("  3. 加权面积 = 建筑面积 × 楼层系数（高层系数高于低层）")
    print()
    print("楼层系数表:")
    for floor in sorted(floor_coefficients.keys()):
        print(f"  {floor} 楼: {floor_coefficients[floor]:.1f}")


if __name__ == "__main__":
    main()
