import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../models/language.dart';
import 'auth_provider.dart';

// ---------------------------------------------------------------------------
// Available languages
// ---------------------------------------------------------------------------

final languagesProvider = FutureProvider<List<Language>>((ref) async {
  final apiClient = ref.watch(apiClientProvider);
  final response = await apiClient.get('/mobile/languages');
  final items = response.data as List<dynamic>;
  return items
      .map((e) => Language.fromJson(e as Map<String, dynamic>))
      .toList();
});

// ---------------------------------------------------------------------------
// User's enrolled languages
// ---------------------------------------------------------------------------

/// Each element is a map containing language info plus user-specific data
/// (e.g. proficiency level). The exact shape depends on the backend response.
typedef UserLanguageInfo = Map<String, dynamic>;

final userLanguagesProvider = FutureProvider<List<UserLanguageInfo>>((ref) async {
  final apiClient = ref.watch(apiClientProvider);
  final response = await apiClient.get('/mobile/users/me/languages');
  final items = response.data as List<dynamic>;
  return items.cast<UserLanguageInfo>();
});

// ---------------------------------------------------------------------------
// Currently selected language
// ---------------------------------------------------------------------------

final selectedLanguageProvider = StateProvider<UserLanguageInfo?>((ref) => null);

/// Currently selected language ID (used by UI that only needs the ID).
final selectedLanguageIdProvider = StateProvider<String?>((ref) => null);

// ---------------------------------------------------------------------------
// CEFR level info for the selected language
// ---------------------------------------------------------------------------

class CefrInfo {
  final String level;
  final double progressPercent;

  CefrInfo({required this.level, required this.progressPercent});
}

final cefrLevelProvider = Provider<AsyncValue<CefrInfo?>>((ref) {
  final selected = ref.watch(selectedLanguageProvider);
  if (selected == null) return const AsyncValue.data(null);

  final level = selected['current_cefr_level'] as String? ?? 'A0';
  final progress = (selected['cefr_progress_percent'] as num?)?.toDouble() ?? 0.0;

  return AsyncValue.data(CefrInfo(level: level, progressPercent: progress));
});
