import 'package:flutter/material.dart';

import '../config/theme.dart';

/// Lightweight data holder for a CEFR level row.
class CefrLevelInfo {
  const CefrLevelInfo({required this.level, required this.status});

  /// E.g. "A1", "B2".
  final String level;

  /// E.g. "PASSED", "IN PROGRESS".
  final String status;
}

/// A tappable tile representing a single CEFR level with its completion status.
class CefrLevelTile extends StatelessWidget {
  const CefrLevelTile({
    super.key,
    required this.info,
    this.isSelected = false,
    required this.onTap,
  });

  final CefrLevelInfo info;
  final bool isSelected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final isPassed =
        info.status.toUpperCase() == 'PASSED';

    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
        decoration: BoxDecoration(
          color: isSelected
              ? AppColors.primary.withValues(alpha: 0.1)
              : AppColors.navBg.withValues(alpha: 0.08),
          borderRadius: BorderRadius.circular(12),
          border: isSelected
              ? Border.all(color: AppColors.primary, width: 1.5)
              : null,
        ),
        child: Row(
          children: [
            // Level label
            Text(
              info.level,
              style: const TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.w700,
                color: AppColors.textPrimary,
              ),
            ),
            const Spacer(),

            // Status chip
            Container(
              padding:
                  const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
              decoration: BoxDecoration(
                color: isPassed
                    ? AppColors.success.withValues(alpha: 0.15)
                    : AppColors.accent.withValues(alpha: 0.18),
                borderRadius: BorderRadius.circular(20),
              ),
              child: Text(
                info.status.toUpperCase(),
                style: TextStyle(
                  fontSize: 11,
                  fontWeight: FontWeight.w700,
                  color: isPassed ? AppColors.success : AppColors.accent,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
