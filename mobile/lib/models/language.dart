class Language {
  final String id;
  final String name;
  final String locale;
  final String? iconUrl;
  final bool isDefault;
  final bool isFallback;
  final bool isActive;

  const Language({
    required this.id,
    required this.name,
    required this.locale,
    this.iconUrl,
    this.isDefault = false,
    this.isFallback = false,
    this.isActive = true,
  });

  factory Language.fromJson(Map<String, dynamic> json) {
    return Language(
      id: json['id'] as String,
      name: json['name'] as String,
      locale: json['locale'] as String,
      iconUrl: json['icon_url'] as String?,
      isDefault: json['is_default'] as bool? ?? false,
      isFallback: json['is_fallback'] as bool? ?? false,
      isActive: json['is_active'] as bool? ?? true,
    );
  }
}
