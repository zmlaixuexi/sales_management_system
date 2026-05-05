import { useState, useEffect } from 'react'
import { Form, Input, InputNumber, Button, Card, Space, Upload, Image, message, Select } from 'antd'
import { PlusOutlined, ArrowLeftOutlined } from '@ant-design/icons'
import { useNavigate, useParams } from 'react-router-dom'
import { fetchProduct, createProduct, updateProduct, uploadImage } from '@/api/products'
import type { ProductDetail, ProductFormValues } from '@/api/products'
import { useSubmit } from '@/hooks/useSubmit'
import { getApiErrorMessage, isToastDisplayed } from '@/utils'
import useDocumentTitle from '@/hooks/useDocumentTitle'
import { useAuthStore } from '@/stores/auth'

export default function ProductForm() {
  useDocumentTitle('商品编辑')
  const navigate = useNavigate()
  const { id } = useParams<{ id: string }>()
  const isEdit = Boolean(id)
  const canSubmit = useAuthStore(s => s.hasPermission(isEdit ? 'product:update' : 'product:create'))
  const [form] = Form.useForm()
  const [loading, setLoading] = useState(false)
  const [_detail, setDetail] = useState<ProductDetail | null>(null)
  const [imageUploading, setImageUploading] = useState(false)
  const [mainImageUrl, setMainImageUrl] = useState<string | null>(null)
  const [showAdvanced, setShowAdvanced] = useState(false)

  useEffect(() => {
    if (id) {
      setLoading(true)
      fetchProduct(id)
        .then((res) => {
          if (res.success) {
            setDetail(res.data)
            setMainImageUrl(res.data.main_image_url)
            form.setFieldsValue({
              name: res.data.name,
              cost_price: res.data.cost_price ? parseFloat(res.data.cost_price) : undefined,
              sale_price: parseFloat(res.data.sale_price),
              sku: res.data.sku,
              stock_quantity: res.data.stock_quantity,
              status: res.data.status,
              sort_weight: res.data.sort_weight,
              remark: res.data.remark,
            })
          }
        })
        .catch((e: unknown) => {
          if (!isToastDisplayed(e)) message.error(getApiErrorMessage(e, '加载商品信息失败'))
          navigate('/products', { replace: true })
        })
        .finally(() => setLoading(false))
    }
  }, [id, form, navigate])

  const handleImageUpload = async (file: File) => {
    setImageUploading(true)
    try {
      const res = await uploadImage(file)
      if (res.success) {
        setMainImageUrl(res.data.url)
        message.success('图片上传成功')
      }
    } catch (e: unknown) {
      if (!isToastDisplayed(e)) message.error('图片上传失败')
    } finally {
      setImageUploading(false)
    }
    return false
  }

  const { submitting, handleSubmit } = useSubmit(async (values: Record<string, unknown>) => {
    const name = values.name as string
    const cost_price = values.cost_price as number | undefined
    const sale_price = values.sale_price as number | undefined
    const sku = values.sku as string | undefined
    const stock_quantity = values.stock_quantity as number | undefined
    const status = values.status as string | undefined
    const sort_weight = values.sort_weight as number | undefined
    const remark = values.remark as string | undefined
    const payload: Partial<ProductFormValues> = {
      name,
      cost_price: cost_price !== null && cost_price !== undefined ? String(cost_price) : undefined,
      sale_price: sale_price !== null && sale_price !== undefined ? String(sale_price) : undefined,
      main_image_url: mainImageUrl ?? undefined,
      sku,
      stock_quantity,
      status,
      sort_weight,
      remark,
    }
    if (isEdit && id) {
      const res = await updateProduct(id, payload)
      if (res.success) {
        message.success('更新成功')
        navigate('/products')
      }
    } else {
      if (payload.cost_price === undefined || payload.sale_price === undefined) {
        throw new Error('请输入成本价和销售价')
      }
      const res = await createProduct({
        ...payload,
        name,
        cost_price: payload.cost_price,
        sale_price: payload.sale_price,
      })
      if (res.success) {
        message.success('创建成功')
        navigate('/products')
      }
    }
  })

  return (
    <div>
      <div style={{ marginBottom: 16 }}>
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/products')}>返回列表</Button>
      </div>
      <Card title={isEdit ? '编辑商品' : '新增商品'} loading={loading || submitting}>
        <Form
          form={form}
          layout="vertical"
          onFinish={handleSubmit}
          initialValues={{ status: 'active', stock_quantity: 0, sort_weight: 0 }}
          style={{ maxWidth: 600, width: '100%' }}
        >
          <Form.Item label="商品名称" name="name" rules={[{ required: true, message: '请输入商品名称' }]}>
            <Input placeholder="请输入商品名称" maxLength={100} />
          </Form.Item>

          <Form.Item label="商品图片" required>
            <Space>
              {mainImageUrl && (
                <Image src={mainImageUrl} width={80} height={80} style={{ objectFit: 'cover', borderRadius: 4 }} />
              )}
              <Upload
                beforeUpload={(file) => { handleImageUpload(file); return false }}
                showUploadList={false}
                accept=".jpg,.jpeg,.png,.webp"
              >
                <Button icon={<PlusOutlined />} loading={imageUploading}>
                  {mainImageUrl ? '替换图片' : '选择图片'}
                </Button>
              </Upload>
            </Space>
          </Form.Item>

          <Space size="large" wrap>
            <Form.Item label="成本价" name="cost_price" rules={[{ required: true, message: '请输入成本价' }]}>
              <InputNumber min={0} precision={2} prefix="¥" style={{ width: 180 }} />
            </Form.Item>
            <Form.Item label="销售价" name="sale_price" rules={[{ required: true, message: '请输入销售价' }]}>
              <InputNumber min={0} precision={2} prefix="¥" style={{ width: 180 }} />
            </Form.Item>
          </Space>

          <Button type="link" onClick={() => setShowAdvanced(!showAdvanced)} style={{ padding: 0, marginBottom: 16 }}>
            {showAdvanced ? '收起高级设置' : '展开高级设置'}
          </Button>

          {showAdvanced && (
            <>
              <Form.Item label="SKU（留空自动生成）" name="sku">
                <Input placeholder="留空自动生成" maxLength={50} disabled={isEdit} />
              </Form.Item>
              <Space size="large" wrap>
                <Form.Item label="库存数量" name="stock_quantity">
                  <InputNumber min={0} precision={0} style={{ width: 180 }} />
                </Form.Item>
                <Form.Item label="排序权重" name="sort_weight">
                  <InputNumber precision={0} style={{ width: 180 }} />
                </Form.Item>
              </Space>
              <Form.Item label="状态" name="status">
                <Select
                  options={[
                    { label: '上架', value: 'active' },
                    { label: '下架', value: 'inactive' },
                    { label: '停用', value: 'disabled' },
                  ]}
                  style={{ width: 180 }}
                />
              </Form.Item>
              <Form.Item label="备注" name="remark">
                <Input.TextArea rows={3} maxLength={500} />
              </Form.Item>
            </>
          )}

          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit" loading={loading || submitting} disabled={!canSubmit}>
                {isEdit ? '保存修改' : '创建商品'}
              </Button>
              <Button onClick={() => navigate('/products')}>取消</Button>
            </Space>
          </Form.Item>
        </Form>
      </Card>
    </div>
  )
}
