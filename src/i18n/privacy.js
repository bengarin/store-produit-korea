/**
 * Politique de confidentialité (FR / AR).
 * Décrit uniquement ce que la boutique fait réellement (voir docs/META_PIXEL.md et le code).
 * ⚠️ Texte d'information NON validé juridiquement : à faire relire avant toute publication.
 * Les éléments que seul le propriétaire peut fournir restent visibles comme « à compléter » (rien n'est inventé).
 */
export const PRIVACY_UPDATED = { fr: '2 novembre 2026', ar: '2 نونبر 2026' };

const TODO = { fr: '[à compléter]', ar: '[يُستكمل لاحقًا]' };

/** `info` = { brand, name, address, email, phone, whatsapp } issus de la configuration de la boutique. */
export function privacySections(lang, info) {
  const todo = TODO[lang];
  const controller = info.name || info.brand;
  const contacts = [info.email, info.phone, info.whatsapp && `WhatsApp +${info.whatsapp}`].filter(Boolean).join(' · ') || todo;
  const address = info.address || todo;

  if (lang === 'ar') {
    return [
      {
        title: 'المسؤول عن معالجة البيانات',
        paragraphs: [`${controller} — العنوان: ${address}.`, `للتواصل: ${contacts}.`],
      },
      {
        title: 'البيانات التي نجمعها',
        list: [
          'عند الطلب: الاسم الكامل، رقم الهاتف، المدينة، العنوان، المنتجات المطلوبة وأي ملاحظة تُضاف إلى الطلب.',
          'عند الاشتراك في النشرة الإخبارية (اختياري): البريد الإلكتروني، وتاريخ الموافقة ونصها.',
          'لأمن الموقع: عنوان IP ونوع المتصفح عند تسجيل الطلب، لمكافحة الاحتيال والطلبات المسيئة.',
          'في متصفحكم فقط (بدون حساب عميل): السلة، المفضلة، اللغة المختارة، اختياركم بشأن ملفات تعريف الارتباط، وآخر طلب لعرض صفحة التأكيد.',
          'قياس الإعلانات: فقط إذا وافقتم على بكسل Meta (انظر أدناه).',
        ],
        paragraphs: ['لا نطلب أي بيانات بنكية: الدفع يتم عند الاستلام.'],
      },
      {
        title: 'لماذا نستعمل هذه البيانات',
        list: [
          'تحضير الطلب وتأكيده هاتفيًا وتوصيله وخدمة ما بعد البيع (تنفيذ الطلب).',
          'إعداد الفواتير وحفظها (التزام قانوني).',
          'حماية المتجر من الاحتيال والاستعمال المسيء (مصلحة مشروعة).',
          'إرسال النشرة الإخبارية إذا وافقتم عليها، مع إمكانية إلغاء الاشتراك في أي وقت.',
          'قياس فعالية إعلاناتنا على فيسبوك وإنستغرام، فقط بموافقتكم.',
        ],
      },
      {
        title: 'ملفات تعريف الارتباط وبكسل Meta',
        paragraphs: [
          'بعض وسائل التخزين ضرورية لعمل المتجر (السلة، اللغة، الأمان) ولا تتطلب موافقة.',
          'بكسل Meta أداة من شركة Meta (فيسبوك وإنستغرام) لقياس فعالية الإعلانات. لا يتم تحميله ولا تُرسل أي بيانات إلى Meta قبل الضغط على «أوافق». في حال الرفض، لا يُحمَّل أي شيء.',
          'بعد الموافقة، تُرسل إلى Meta المعلومات التالية: الصفحات التي تمت زيارتها، والمنتجات المعروضة، والإضافة إلى السلة أو المفضلة أو الحذف منها، وبدء الطلب، والطلب المسجّل (المنتجات، المبلغ، رقم الطلب)، والنقر على روابط التواصل، إضافة إلى بيانات تقنية (عنوان IP، المتصفح، ملفات تعريف ارتباط خاصة بـ Meta). لا نرسل إلى Meta الاسم ولا رقم الهاتف ولا العنوان.',
          'قد تعالج Meta هذه البيانات خارج المغرب وفق سياستها الخاصة: https://www.facebook.com/privacy/policy/',
          'يمكنكم تغيير اختياركم في أي وقت عبر الزر أدناه أو رابط «ملفات تعريف الارتباط» أسفل كل صفحة.',
        ],
        consentButton: true,
      },
      {
        title: 'من يطّلع على البيانات',
        list: [
          'فريق المتجر المخوّل فقط (حسب الدور، مع تحقق بخطوتين للمسؤولين).',
          `شركة التوصيل: الاسم والهاتف والعنوان اللازمة للتوصيل — ${todo}.`,
          `مزودو الخدمات التقنية (الاستضافة، إرسال الرسائل الإلكترونية) — ${todo}.`,
          'شركة Meta، فقط في حال الموافقة على البكسل.',
        ],
        paragraphs: ['لا نبيع بياناتكم.'],
      },
      {
        title: 'مدة الحفظ',
        paragraphs: [`مدة حفظ بيانات الطلبات والعملاء والنشرة الإخبارية: ${todo}. ملفات تعريف ارتباط Meta: حسب المدة التي تحددها Meta.`],
      },
      {
        title: 'حقوقكم',
        paragraphs: [
          'وفقًا للقانون المغربي رقم 09-08 المتعلق بحماية الأشخاص الذاتيين تجاه معالجة المعطيات ذات الطابع الشخصي، يحق لكم الاطلاع على بياناتكم وتصحيحها والاعتراض على معالجتها لأسباب مشروعة، والاعتراض على الاستعمال لأغراض الاستشهار.',
          `لممارسة هذه الحقوق: ${contacts}. يمكنكم أيضًا التوجه إلى اللجنة الوطنية لمراقبة حماية المعطيات ذات الطابع الشخصي (CNDP): www.cndp.ma`,
        ],
      },
      {
        title: 'تعديل هذه السياسة',
        paragraphs: ['قد يتم تحديث هذه الصفحة. يُذكر تاريخ آخر تحديث في أعلاها.'],
      },
    ];
  }

  return [
    {
      title: 'Responsable du traitement',
      paragraphs: [`${controller} — adresse : ${address}.`, `Contact : ${contacts}.`],
    },
    {
      title: 'Données collectées',
      list: [
        'Lors d’une commande : nom complet, téléphone, ville, adresse, produits commandés et note éventuelle.',
        'Inscription à la newsletter (facultative) : adresse e-mail, date et texte du consentement.',
        'Sécurité : adresse IP et type de navigateur lors de l’enregistrement d’une commande, pour lutter contre la fraude et les abus.',
        'Dans votre navigateur uniquement (aucun compte client) : panier, favoris, langue choisie, votre choix concernant les cookies et la dernière commande (page de confirmation).',
        'Mesure publicitaire : seulement si vous acceptez le pixel Meta (voir ci-dessous).',
      ],
      paragraphs: ['Aucune donnée bancaire n’est demandée : le paiement se fait à la livraison.'],
    },
    {
      title: 'Pourquoi nous utilisons ces données',
      list: [
        'Préparer, confirmer par téléphone et livrer la commande, assurer le service après-vente (exécution de la commande).',
        'Établir et conserver les factures (obligation légale).',
        'Protéger la boutique contre la fraude et les abus (intérêt légitime).',
        'Envoyer la newsletter si vous l’avez acceptée ; désinscription possible à tout moment.',
        'Mesurer l’efficacité de nos publicités sur Facebook et Instagram, uniquement avec votre accord.',
      ],
    },
    {
      title: 'Cookies et pixel Meta',
      paragraphs: [
        'Certains stockages sont indispensables au fonctionnement de la boutique (panier, langue, sécurité) et ne demandent pas de consentement.',
        'Le pixel Meta est un outil de Meta (Facebook, Instagram) qui mesure l’efficacité des publicités. Il n’est pas chargé et aucune donnée n’est envoyée à Meta avant que vous cliquiez sur « Accepter ». Si vous refusez, rien n’est chargé.',
        'Après acceptation, sont transmis à Meta : les pages visitées, les produits consultés, les ajouts et retraits du panier ou des favoris, le début de commande, la commande enregistrée (produits, montant, numéro de commande), les clics sur les liens de contact, ainsi que des données techniques (adresse IP, navigateur, cookies propres à Meta). Nous n’envoyons à Meta ni votre nom, ni votre téléphone, ni votre adresse.',
        'Meta peut traiter ces données hors du Maroc, selon sa propre politique : https://www.facebook.com/privacy/policy/',
        'Vous pouvez changer d’avis à tout moment avec le bouton ci-dessous ou le lien « Cookies » en bas de chaque page.',
      ],
      consentButton: true,
    },
    {
      title: 'Qui a accès aux données',
      list: [
        'L’équipe autorisée de la boutique uniquement (accès selon le rôle, double authentification pour les responsables).',
        `Le livreur : nom, téléphone et adresse nécessaires à la livraison — ${todo}.`,
        `Les prestataires techniques (hébergement, envoi d’e-mails) — ${todo}.`,
        'Meta, uniquement si vous avez accepté le pixel.',
      ],
      paragraphs: ['Nous ne vendons pas vos données.'],
    },
    {
      title: 'Durée de conservation',
      paragraphs: [`Données de commande, clients et newsletter : ${todo}. Cookies Meta : durée fixée par Meta.`],
    },
    {
      title: 'Vos droits',
      paragraphs: [
        'Conformément à la loi marocaine n° 09-08 relative à la protection des personnes physiques à l’égard du traitement des données à caractère personnel, vous pouvez accéder à vos données, les faire rectifier, vous opposer à leur traitement pour des motifs légitimes et vous opposer à leur utilisation à des fins de prospection.',
        `Pour exercer ces droits : ${contacts}. Vous pouvez aussi vous adresser à la Commission nationale de contrôle de la protection des données à caractère personnel (CNDP) : www.cndp.ma`,
      ],
    },
    {
      title: 'Modifications',
      paragraphs: ['Cette page peut être mise à jour. La date de dernière mise à jour figure en haut de la page.'],
    },
  ];
}
