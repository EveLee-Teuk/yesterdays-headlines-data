export type NewsArticle = {
  id: string;
  originalHeadline: string;
  articleBody: string;
  category: '民生' | '科技' | '社会';
  location: string;
  timestamp: string;
  imageId: string;
};

export const NEWS_DATA: NewsArticle[] = [
  {
    id: '1',
    originalHeadline: "中国首颗量子科学实验卫星“墨子号”完成全部预定科学目标",
    articleBody: "2017年6月2日，中国科学院宣布，世界首颗量子科学实验卫星“墨子号”在轨运行近一年后，圆满完成了星地量子密钥分发、量子纠缠分发和量子隐形传态三大科学实验任务，标志着中国在量子通信领域迈入世界领先行列。",
    category: '科技',
    location: '北京',
    timestamp: '2017年',
    imageId: 'tech-1'
  },
  {
    id: '2',
    originalHeadline: "三峡工程完成全线挡水验收",
    articleBody: "2006年6月2日，长江三峡水利枢纽工程右岸大坝全线浇筑至185米设计高程，标志着三峡大坝全线建成并具备全线挡水能力。这一世界最大水利枢纽工程在防洪、发电、航运等方面发挥巨大综合效益，显著提升了长江中下游地区的民生安全保障。",
    category: '民生',
    location: '湖北宜昌',
    timestamp: '2006年',
    imageId: 'livelihood-1'
  },
  {
    id: '3',
    originalHeadline: "中国成功发射“实践六号”空间环境探测卫星",
    articleBody: "2004年6月2日，我国在太原卫星发射中心用“长征二号丙”运载火箭，成功将“实践六号”A、B两颗空间环境探测卫星送入预定轨道。该卫星主要用于探测空间环境参数，为航天器安全运行和空间科学研究提供重要数据支持。",
    category: '科技',
    location: '太原卫星发射中心',
    timestamp: '2004年',
    imageId: 'tech-2'
  }
];