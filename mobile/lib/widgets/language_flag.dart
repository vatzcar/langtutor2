import 'package:flutter/material.dart';

/// Lightweight data holder for a language with its flag.
class Language {
  const Language({required this.name, this.iconUrl});

  final String name;

  /// Network URL for the flag image. Falls back to a generic icon.
  final String? iconUrl;
}

/// A tappable row showing a language flag and name, styled for dark backgrounds.
class LanguageFlag extends StatelessWidget {
  const LanguageFlag({
    super.key,
    required this.language,
    required this.onTap,
  });

  final Language language;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
        decoration: BoxDecoration(
          color: Colors.white12,
          borderRadius: BorderRadius.circular(10),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            _buildFlag(),
            const SizedBox(width: 8),
            Text(
              language.name,
              style: const TextStyle(
                color: Colors.white,
                fontSize: 14,
                fontWeight: FontWeight.w600,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildFlag() {
    if (language.iconUrl != null && language.iconUrl!.isNotEmpty) {
      return ClipRRect(
        borderRadius: BorderRadius.circular(3),
        child: Image.network(
          language.iconUrl!,
          width: 24,
          height: 18,
          fit: BoxFit.cover,
          errorBuilder: (_, __, ___) => const Icon(
            Icons.flag,
            size: 20,
            color: Colors.white,
          ),
        ),
      );
    }
    return const Icon(
      Icons.flag,
      size: 20,
      color: Colors.white,
    );
  }
}
