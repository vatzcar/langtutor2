class Persona {
  final String id;
  final String name;
  final String languageId;
  final String? imageUrl;
  final String gender;
  final String type;
  final String? teachingStyle;
  final bool isActive;

  const Persona({
    required this.id,
    required this.name,
    required this.languageId,
    this.imageUrl,
    required this.gender,
    required this.type,
    this.teachingStyle,
    this.isActive = true,
  });

  factory Persona.fromJson(Map<String, dynamic> json) {
    return Persona(
      id: json['id'] as String,
      name: json['name'] as String,
      languageId: json['language_id'] as String,
      imageUrl: json['image_url'] as String?,
      gender: json['gender'] as String,
      type: json['type'] as String,
      teachingStyle: json['teaching_style'] as String?,
      isActive: json['is_active'] as bool? ?? true,
    );
  }
}
